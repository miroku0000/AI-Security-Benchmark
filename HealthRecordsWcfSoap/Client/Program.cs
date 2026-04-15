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
