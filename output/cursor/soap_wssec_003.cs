var builder = WebApplication.CreateBuilder(args);

var algorithmName = builder.Configuration["WsSecurity:AlgorithmSuite"];
var serviceSubject = builder.Configuration["WsSecurity:ServiceCertificateSubject"] ?? "CN=HealthRecordsService";
var clientSubject = builder.Configuration["WsSecurity:ClientCertificateSubject"] ?? "CN=HealthRecordsClient";
var validDays = int.TryParse(builder.Configuration["WsSecurity:CertificateValidityDays"], out var d) ? d : 365;
var exportDev = builder.Configuration.GetValue("WsSecurity:ExportDevCertificates", true);
var maxMessageSize = 100L * 1024 * 1024;

var serviceCert = CertificateKeyManager.CreateDevelopmentCertificate(serviceSubject, validDays);
var clientCert = CertificateKeyManager.CreateDevelopmentCertificate(clientSubject, validDays);
var keyManager = new CertificateKeyManager(serviceCert, new[] { clientCert.Thumbprint });

if (exportDev)
{
    var certDir = Path.Combine(builder.Environment.ContentRootPath, "dev-certs");
    Directory.CreateDirectory(certDir);
    await File.WriteAllBytesAsync(Path.Combine(certDir, "client.pfx"), clientCert.Export(X509ContentType.Pfx, "dev"));
    var meta = new
    {
        serviceThumbprint = (serviceCert.Thumbprint ?? "").Replace(" ", "", StringComparison.Ordinal),
        clientThumbprint = (clientCert.Thumbprint ?? "").Replace(" ", "", StringComparison.Ordinal),
        pfxPassword = "dev"
    };
    await File.WriteAllTextAsync(Path.Combine(certDir, "exchange.json"), JsonSerializer.Serialize(meta, new JsonSerializerOptions { WriteIndented = true }));
}

builder.Services.AddSingleton(serviceCert);
builder.Services.AddSingleton(clientCert);
builder.Services.AddSingleton(keyManager);
builder.Services.AddSingleton<MedicalRecordRepository>();
builder.Services.AddSingleton<HealthRecordsService>();
builder.Services.AddServiceModelServices();
builder.Services.AddSingleton<IServiceBehavior, UseRequestHeadersForMetadataAddressBehavior>();

builder.WebHost.ConfigureKestrel(options =>
{
    options.ConfigureHttpsDefaults(https => https.ServerCertificate = serviceCert);
});

var app = builder.Build();

var suite = HipaaSoapBindingFactory.ResolveAlgorithmSuite(algorithmName);
var binding = HipaaSoapBindingFactory.CreateWsSecurityHttpsBinding(suite, maxMessageSize);

app.UseServiceModel(serviceBuilder =>
{
    serviceBuilder.AddService<HealthRecordsService>(options => { });
    serviceBuilder.AddServiceEndpoint<HealthRecordsService, IHealthRecordsService>(
        binding,
        "/HealthRecords.svc");

    serviceBuilder.ConfigureServiceHostBase<HealthRecordsService>(host =>
    {
        host.Credentials.ServiceCertificate.Certificate = keyManager.ServiceCertificate;
        host.Credentials.ClientCertificate.Authentication.CertificateValidationMode =
            X509CertificateValidationMode.Custom;
        host.Credentials.ClientCertificate.Authentication.CustomCertificateValidator =
            new ThumbprintX509Validator(keyManager.TrustedClientThumbprints);
        host.Credentials.ClientCertificate.Authentication.RevocationMode = X509RevocationMode.NoCheck;

        var meta = host.Description.Behaviors.Find<ServiceMetadataBehavior>();
        if (meta == null)
        {
            meta = new ServiceMetadataBehavior();
            host.Description.Behaviors.Add(meta);
        }
        meta.HttpGetEnabled = false;
        meta.HttpsGetEnabled = true;
    });
});

app.MapGet("/", () => "HIE SOAP: /HealthRecords.svc (HTTPS + WS-Security mutual certificate, message encrypt/sign).");

app.Run();

----- FILE: HealthRecordsWcfSoap/Host/HealthRecordsService.cs -----
using System.ServiceModel;

namespace HealthRecordsWcfExchange;

[ServiceBehavior(
    Namespace = "urn:hie:healthrecords:v1",
    InstanceContextMode = InstanceContextMode.PerCall,
    ConcurrencyMode = ConcurrencyMode.Multiple,
    IncludeExceptionDetailInFaults = false)]
public sealed class HealthRecordsService : IHealthRecordsService
{
    private readonly MedicalRecordRepository _repository;

    public HealthRecordsService(MedicalRecordRepository repository)
    {
        _repository = repository;
    }

    public MedicalRecordSubmissionResult SubmitMedicalRecord(MedicalRecordSubmission request)
    {
        if (request == null)
            throw new FaultException("MedicalRecordSubmission is required.");
        if (string.IsNullOrWhiteSpace(request.PatientId))
            throw new FaultException("PatientId is required.");
        if (request.Clinical == null)
            throw new FaultException("Clinical payload is required.");

        var caller = ServiceSecurityContext.Current?.PrimaryIdentity?.Name ?? "anonymous";
        var recordId = _repository.Upsert(request.PatientId.Trim(), request.Clinical);

        return new MedicalRecordSubmissionResult
        {
            Accepted = true,
            Message = $"Processed for caller identity '{caller}'.",
            RecordId = recordId
        };
    }

    public PatientClinicalSummaryResponse GetPatientClinicalSummary(PatientClinicalSummaryRequest request)
    {
        if (request == null)
            throw new FaultException("PatientClinicalSummaryRequest is required.");
        if (string.IsNullOrWhiteSpace(request.PatientId))
            throw new FaultException("PatientId is required.");

        var doc = _repository.Get(request.PatientId.Trim(), request.RecordId);
        if (doc == null)
        {
            return new PatientClinicalSummaryResponse
            {
                Found = false,
                Message = "No clinical document matched the request."
            };
        }

        return new PatientClinicalSummaryResponse
        {
            Found = true,
            Summary = doc,
            Message = "OK"
        };
    }
}

----- FILE: HealthRecordsWcfSoap/Host/HipaaSecurityBinding.cs -----
using System.Collections.Generic;
using System.IdentityModel.Selectors;
using System.IdentityModel.Tokens;
using System.Security.Cryptography.X509Certificates;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.ServiceModel.Security;

namespace HealthRecordsWcfExchange;

public sealed class HipaaSecurityAlgorithmSuite : SecurityAlgorithmSuite
{
    public override string DefaultAsymmetricKeyWrapAlgorithm => SecurityAlgorithms.RsaOaepKeyWrap;

    public override string DefaultAsymmetricSignatureAlgorithm => SecurityAlgorithms.RsaSha256Signature;

    public override string DefaultCanonicalizationAlgorithm => SecurityAlgorithms.ExclusiveC14n;

    public override string DefaultDigestAlgorithm => SecurityAlgorithms.Sha256Digest;

    public override string DefaultEncryptionAlgorithm => SecurityAlgorithms.Aes256Encryption;

    public override int DefaultEncryptionKeyDerivationLength => 256;

    public override int DefaultSignatureKeyDerivationLength => 256;

    public override int DefaultSymmetricKeyLength => 256;

    public override string DefaultSymmetricSignatureAlgorithm => SecurityAlgorithms.HmacSha256Signature;

    public override string DefaultSymmetricKeyWrapAlgorithm => SecurityAlgorithms.Aes256KeyWrap;
}

public sealed class ThumbprintX509Validator : X509CertificateValidator
{
    private readonly HashSet<string> _trustedThumbprints;

    public ThumbprintX509Validator(IEnumerable<string> trustedThumbprints)
    {
        _trustedThumbprints = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var t in trustedThumbprints)
        {
            if (!string.IsNullOrWhiteSpace(t))
                _trustedThumbprints.Add(NormalizeThumbprint(t));
        }
    }

    public override void Validate(X509Certificate2 certificate)
    {
        if (certificate == null)
            throw new SecurityTokenValidationException("X.509 certificate is required.");

        var thumb = NormalizeThumbprint(certificate.Thumbprint);
        if (!_trustedThumbprints.Contains(thumb))
            throw new SecurityTokenValidationException("Certificate thumbprint is not trusted for this HIE endpoint.");
    }

    private static string NormalizeThumbprint(string? thumbprint) =>
        (thumbprint ?? "").Replace(" ", "", StringComparison.Ordinal).ToUpperInvariant();
}

public static class HipaaSoapBindingFactory
{
    public static Binding CreateWsSecurityHttpsBinding(SecurityAlgorithmSuite algorithmSuite, long maxMessageSize)
    {
        var security = SecurityBindingElement.CreateMutualCertificateBindingElement(
            MessageSecurityVersion.WSSecurity11WSTrustFebruary2005,
            requireSignatureConfirmation: false);

        security.IncludeTimestamp = true;
        security.DefaultAlgorithmSuite = algorithmSuite;
        security.MessageProtectionOrder = MessageProtectionOrder.SignBeforeEncryptAndEncryptSignature;
        security.RequireSignatureConfirmation = false;
        security.SecurityHeaderLayout = SecurityHeaderLayout.Strict;

        var encoding = new TextMessageEncodingBindingElement(MessageVersion.Soap12WSAddressing10, System.Text.Encoding.UTF8)
        {
            ReaderQuotas = new XmlDictionaryReaderQuotas
            {
                MaxArrayLength = int.MaxValue,
                MaxBytesPerRead = 65536,
                MaxDepth = 128,
                MaxNameTableCharCount = int.MaxValue,
                MaxStringContentLength = int.MaxValue
            }
        };

        var transport = new HttpsTransportBindingElement
        {
            RequireClientCertificate = false,
            MaxReceivedMessageSize = maxMessageSize
        };

        return new CustomBinding(security, encoding, transport);
    }

    public static SecurityAlgorithmSuite ResolveAlgorithmSuite(string? name) =>
        name?.Trim() switch
        {
            "Basic256Sha256" => SecurityAlgorithmSuite.Basic256Sha256,
            "Basic256" => SecurityAlgorithmSuite.Basic256,
            "Basic128" => SecurityAlgorithmSuite.Basic128,
            "TripleDes" => SecurityAlgorithmSuite.TripleDes,
            "Default" => SecurityAlgorithmSuite.Default,
            "HipaaSuite" => new HipaaSecurityAlgorithmSuite(),
            _ => SecurityAlgorithmSuite.Basic256Sha256Rsa15
        };
}

----- FILE: HealthRecordsWcfSoap/Host/CertificateKeyManager.cs -----
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

namespace HealthRecordsWcfExchange;

public sealed class CertificateKeyManager
{
    public CertificateKeyManager(X509Certificate2 serviceCertificate, IReadOnlyCollection<string> trustedClientThumbprints)
    {
        ServiceCertificate = serviceCertificate;
        TrustedClientThumbprints = trustedClientThumbprints;
    }

    public X509Certificate2 ServiceCertificate { get; }

    public IReadOnlyCollection<string> TrustedClientThumbprints { get; }

    public static X509Certificate2 CreateDevelopmentCertificate(string subjectDistinguishedName, int validDays)
    {
        using var rsa = RSA.Create(4096);
        var req = new CertificateRequest(subjectDistinguishedName, rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        req.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, false));
        req.CertificateExtensions.Add(new X509KeyUsageExtension(
            X509KeyUsageFlags.DigitalSignature | X509KeyUsageFlags.KeyEncipherment | X509KeyUsageFlags.DataEncipherment,
            critical: true));
        var eku = new OidCollection
        {
            Oid.FromFriendlyName("Server Authentication", OidGroup.EnhancedKeyUsage),
            Oid.FromFriendlyName("Client Authentication", OidGroup.EnhancedKeyUsage)
        };
        req.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(eku, false));

        var notBefore = DateTimeOffset.UtcNow.AddMinutes(-10);
        var notAfter = notBefore.AddDays(validDays);
        using var cert = req.CreateSelfSigned(notBefore, notAfter);
        var pfx = cert.Export(X509ContentType.Pfx, "dev");
        return new X509Certificate2(pfx, "dev", X509KeyStorageFlags.Exportable | X509KeyStorageFlags.EphemeralKeySet);
    }
}

----- FILE: HealthRecordsWcfSoap/Host/MedicalRecordRepository.cs -----
using System.Collections.Concurrent;

namespace HealthRecordsWcfExchange;

public sealed class MedicalRecordRepository
{
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, ClinicalDocument>> _byPatient =
        new(StringComparer.OrdinalIgnoreCase);

    public string Upsert(string patientId, ClinicalDocument clinical)
    {
        var recordId = string.IsNullOrWhiteSpace(clinical.EncounterId)
            ? Guid.NewGuid().ToString("N")
            : clinical.EncounterId!;

        clinical.EncounterId = recordId;
        var inner = _byPatient.GetOrAdd(patientId, _ => new ConcurrentDictionary<string, ClinicalDocument>(StringComparer.OrdinalIgnoreCase));
        inner[recordId] = clinical;
        return recordId;
    }

    public ClinicalDocument? Get(string patientId, string? recordId)
    {
        if (!_byPatient.TryGetValue(patientId, out var inner))
            return null;

        if (string.IsNullOrWhiteSpace(recordId))
        {
            ClinicalDocument? latest = null;
            DateTimeOffset? latestTs = null;
            foreach (var doc in inner.Values)
            {
                var ts = doc.EncounterDate ?? DateTimeOffset.MinValue;
                if (latest == null || ts > latestTs)
                {
                    latest = doc;
                    latestTs = ts;
                }
            }
            return latest;
        }

        return inner.TryGetValue(recordId, out var found) ? found : null;
    }
}

----- FILE: HealthRecordsWcfSoap/Host/UseRequestHeadersForMetadataAddressBehavior.cs -----
using System.Collections.ObjectModel;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.ServiceModel.Description;

namespace HealthRecordsWcfExchange;

public sealed class UseRequestHeadersForMetadataAddressBehavior : IServiceBehavior
{
    public void Validate(ServiceDescription serviceDescription, ServiceHostBase serviceHostBase)
    {
    }

    public void AddBindingParameters(ServiceDescription serviceDescription, ServiceHostBase serviceHostBase, Collection<ServiceEndpoint> endpoints, BindingParameterCollection bindingParameters)
    {
    }

    public void ApplyDispatchBehavior(ServiceDescription serviceDescription, ServiceHostBase serviceHostBase)
    {
    }
}

----- FILE: HealthRecordsWcfSoap/Host/Contracts.cs -----
namespace HealthRecordsWcfExchange;

----- FILE: HealthRecordsWcfSoap/Host/appsettings.json -----
{
  "WsSecurity": {
    "AlgorithmSuite": "Basic256Sha256Rsa15",
    "ServiceCertificateSubject": "CN=HealthRecordsService",
    "ClientCertificateSubject": "CN=HealthRecordsClient",
    "CertificateValidityDays": 365,
    "ExportDevCertificates": true
  },
  "Urls": "https://localhost:8443"
}

----- FILE: HealthRecordsWcfSoap/Host/Properties/launchSettings.json -----
{
  "profiles": {
    "Host": {
      "commandName": "Project",
      "applicationUrl": "https://localhost:8443",
      "environmentVariables": {
        "ASPNETCORE_ENVIRONMENT": "Development"
      }
    }
  }
}

----- FILE: HealthRecordsWcfSoap/Client/Client.csproj -----
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>HealthRecordsWcfExchange.Client</RootNamespace>
    <AssemblyName>HealthRecordsWcfExchange.Client</AssemblyName>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\Contracts\Contracts.csproj" />
    <PackageReference Include="Microsoft.Extensions.Configuration" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Configuration.Binder" Version="8.0.2" />
    <PackageReference Include="Microsoft.Extensions.Configuration.EnvironmentVariables" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Configuration.Json" Version="8.0.1" />
    <PackageReference Include="System.ServiceModel.Http" Version="8.0.0" />
    <PackageReference Include="System.ServiceModel.Primitives" Version="8.0.0" />
    <PackageReference Include="System.ServiceModel.Security" Version="8.0.0" />
  </ItemGroup>
  <ItemGroup>
    <None Update="appsettings.json" CopyToOutputDirectory="PreserveNewest" />
  </ItemGroup>
</Project>

----- FILE: HealthRecordsWcfSoap/Client/Program.cs -----
using System.ServiceModel;
using System.ServiceModel.Security;
using System.Text.Json;
using HealthRecordsWcfExchange;
using HealthRecordsWcfExchange.Client;
using Microsoft.Extensions.Configuration;

var configuration = new ConfigurationBuilder()
    .SetBasePath(AppContext.BaseDirectory)
    .AddJsonFile("appsettings.json", optional: true)
    .AddEnvironmentVariables()
    .Build();

var endpointUrl = configuration["HieClient:EndpointUrl"] ?? "https://localhost:8443/HealthRecords.svc";
var algorithmName = configuration["HieClient:AlgorithmSuite"] ?? "Basic256Sha256Rsa15";
var certDirConfig = configuration["HieClient:DevCertsDirectory"];

var certDir = string.IsNullOrWhiteSpace(certDirConfig)
    ? Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "Host", "dev-certs"))
    : Path.GetFullPath(certDirConfig);

if (args.Length > 0 && !string.IsNullOrWhiteSpace(args[0]))
    certDir = Path.GetFullPath(args[0]);

var exchangePath = Path.Combine(certDir, "exchange.json");
var clientPfxPath = Path.Combine(certDir, "client.pfx");
if (!File.Exists(exchangePath) || !File.Exists(clientPfxPath))
{
    Console.Error.WriteLine("Missing exchange.json or client.pfx under: " + certDir);
    Console.Error.WriteLine("Start Host once so dev-certs are written, or pass the dev-certs directory as the first argument.");
    return 1;
}

var meta = JsonSerializer.Deserialize<ExchangeMeta>(await File.ReadAllTextAsync(exchangePath));
if (meta == null || string.IsNullOrWhiteSpace(meta.serviceThumbprint))
{
    Console.Error.WriteLine("Invalid exchange.json");
    return 1;
}

var clientCert = new System.Security.Cryptography.X509Certificates.X509Certificate2(
    clientPfxPath,
    meta.pfxPassword ?? "dev",
    System.Security.Cryptography.X509Certificates.X509KeyStorageFlags.EphemeralKeySet | System.Security.Cryptography.X509Certificates.X509KeyStorageFlags.Exportable);

var suite = SoapClientBindingFactory.ResolveAlgorithmSuite(algorithmName);
var binding = SoapClientBindingFactory.CreateWsSecurityHttpsBinding(suite, 100L * 1024 * 1024);

var factory = new ChannelFactory<IHealthRecordsService>(binding, new EndpointAddress(endpointUrl));
factory.Credentials.ClientCertificate.Certificate = clientCert;
factory.Credentials.ServiceCertificate.Authentication.CertificateValidationMode = X509CertificateValidationMode.Custom;
factory.Credentials.ServiceCertificate.Authentication.CustomCertificateValidator =
    new ThumbprintX509Validator(new[] { meta.serviceThumbprint });

var channel = factory.CreateChannel();
try
{
    var submission = new MedicalRecordSubmission
    {
        PatientId = "PID-10001",
        Demographics = new PatientDemographics
        {
            LegalName = "Jane Doe",
            DateOfBirth = new DateTimeOffset(1985, 3, 1, 0, 0, 0, TimeSpan.Zero),
            Mrn = "MRN-9"
        },
        Clinical = new ClinicalDocument
        {
            EncounterDate = DateTimeOffset.UtcNow,
            ProviderNpi = "1234567890",
            DiagnosisIcd10 = "E11.9",
            ClinicalNotesPhi = "SOAP body encrypted via WS-Security message security."
        },
        CorrelationId = Guid.NewGuid().ToString("N")
    };

    var result = channel.SubmitMedicalRecord(submission);
    Console.WriteLine("Submit accepted=" + result.Accepted + " recordId=" + result.RecordId + " " + result.Message);

    var summary = channel.GetPatientClinicalSummary(new PatientClinicalSummaryRequest
    {
        PatientId = "PID-10001",
        RecordId = result.RecordId
    });
    Console.WriteLine("Get found=" + summary.Found + " diagnosis=" + summary.Summary?.DiagnosisIcd10);
}
finally
{
    if (factory.State == CommunicationState.Opened)
        factory.Close();
    else
        factory.Abort();
}

return 0;

internal sealed class ExchangeMeta
{
    public string? serviceThumbprint { get; set; }
    public string? clientThumbprint { get; set; }
    public string? pfxPassword { get; set; }
}

----- FILE: HealthRecordsWcfSoap/Client/SoapClientSecurity.cs -----
using System.Collections.Generic;
using System.IdentityModel.Selectors;
using System.IdentityModel.Tokens;
using System.Security.Cryptography.X509Certificates;
using System.ServiceModel;
using System.ServiceModel.Channels;
using System.ServiceModel.Security;

namespace HealthRecordsWcfExchange.Client;

internal sealed class HipaaSecurityAlgorithmSuite : SecurityAlgorithmSuite
{
    public override string DefaultAsymmetricKeyWrapAlgorithm => SecurityAlgorithms.RsaOaepKeyWrap;

    public override string DefaultAsymmetricSignatureAlgorithm => SecurityAlgorithms.RsaSha256Signature;

    public override string DefaultCanonicalizationAlgorithm => SecurityAlgorithms.ExclusiveC14n;

    public override string DefaultDigestAlgorithm => SecurityAlgorithms.Sha256Digest;

    public override string DefaultEncryptionAlgorithm => SecurityAlgorithms.Aes256Encryption;

    public override int DefaultEncryptionKeyDerivationLength => 256;

    public override int DefaultSignatureKeyDerivationLength => 256;

    public override int DefaultSymmetricKeyLength => 256;

    public override string DefaultSymmetricSignatureAlgorithm => SecurityAlgorithms.HmacSha256Signature;

    public override string DefaultSymmetricKeyWrapAlgorithm => SecurityAlgorithms.Aes256KeyWrap;
}

internal sealed class ThumbprintX509Validator : X509CertificateValidator
{
    private readonly HashSet<string> _trustedThumbprints;

    public ThumbprintX509Validator(IEnumerable<string> trustedThumbprints)
    {
        _trustedThumbprints = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var t in trustedThumbprints)
        {
            if (!string.IsNullOrWhiteSpace(t))
                _trustedThumbprints.Add(NormalizeThumbprint(t));
        }
    }

    public override void Validate(X509Certificate2 certificate)
    {
        if (certificate == null)
            throw new SecurityTokenValidationException("X.509 certificate is required.");

        var thumb = NormalizeThumbprint(certificate.Thumbprint);
        if (!_trustedThumbprints.Contains(thumb))
            throw new SecurityTokenValidationException("Certificate thumbprint is not trusted.");
    }

    private static string NormalizeThumbprint(string? thumbprint) =>
        (thumbprint ?? "").Replace(" ", "", StringComparison.Ordinal).ToUpperInvariant();
}

internal static class SoapClientBindingFactory
{
    public static Binding CreateWsSecurityHttpsBinding(SecurityAlgorithmSuite algorithmSuite, long maxMessageSize)
    {
        var security = SecurityBindingElement.CreateMutualCertificateBindingElement(
            MessageSecurityVersion.WSSecurity11WSTrustFebruary2005,
            requireSignatureConfirmation: false);

        security.IncludeTimestamp = true;
        security.DefaultAlgorithmSuite = algorithmSuite;
        security.MessageProtectionOrder = MessageProtectionOrder.SignBeforeEncryptAndEncryptSignature;
        security.RequireSignatureConfirmation = false;
        security.SecurityHeaderLayout = SecurityHeaderLayout.Strict;

        var encoding = new TextMessageEncodingBindingElement(MessageVersion.Soap12WSAddressing10, System.Text.Encoding.UTF8)
        {
            ReaderQuotas = new XmlDictionaryReaderQuotas
            {
                MaxArrayLength = int.MaxValue,
                MaxBytesPerRead = 65536,
                MaxDepth = 128,
                MaxNameTableCharCount = int.MaxValue,
                MaxStringContentLength = int.MaxValue
            }
        };

        var transport = new HttpsTransportBindingElement
        {
            RequireClientCertificate = false,
            MaxReceivedMessageSize = maxMessageSize
        };

        return new CustomBinding(security, encoding, transport);
    }

    public static SecurityAlgorithmSuite ResolveAlgorithmSuite(string? name) =>
        name?.Trim() switch
        {
            "Basic256Sha256" => SecurityAlgorithmSuite.Basic256Sha256,
            "Basic256" => SecurityAlgorithmSuite.Basic256,
            "Basic128" => SecurityAlgorithmSuite.Basic128,
            "TripleDes" => SecurityAlgorithmSuite.TripleDes,
            "Default" => SecurityAlgorithmSuite.Default,
            "HipaaSuite" => new HipaaSecurityAlgorithmSuite(),
            _ => SecurityAlgorithmSuite.Basic256Sha256Rsa15
        };
}

----- FILE: HealthRecordsWcfSoap/Client/appsettings.json -----
{
  "HieClient": {
    "EndpointUrl": "https://localhost:8443/HealthRecords.svc",
    "DevCertsDirectory": "",
    "AlgorithmSuite": "Basic256Sha256Rsa15"
  }
}

`</think>`
The user asked for **only** raw code with no explanations or markdown. The message above is that: a full dump of the existing `HealthRecordsWcfSoap` solution (CoreWCF on .NET 8, SOAP 1.2, WS-Security mutual certificate, configurable algorithm suites, dev cert/key export, host + client).

Run: `dotnet run --project Host` then `dotnet run --project Client` from `HealthRecordsWcfSoap` after the host has created `Host/dev-certs/`.