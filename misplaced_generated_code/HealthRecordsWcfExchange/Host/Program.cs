using System.ServiceModel;
using System.ServiceModel.Channels;
using System.ServiceModel.Description;
using System.ServiceModel.Security;
using CoreWcf;
using CoreWcf.Configuration;
using HealthRecordsWcfExchange;

var builder = WebApplication.CreateBuilder(args);

var algorithmName = builder.Configuration["WsSecurity:AlgorithmSuite"];
var serviceSubject = builder.Configuration["WsSecurity:ServiceCertificateSubject"] ?? "CN=HealthRecordsService";
var clientSubject = builder.Configuration["WsSecurity:ClientCertificateSubject"] ?? "CN=HealthRecordsClient";
var validDays = int.TryParse(builder.Configuration["WsSecurity:CertificateValidityDays"], out var d) ? d : 365;
var maxMessageSize = 100L * 1024 * 1024;

var serviceCert = CertificateKeyManager.CreateDevelopmentCertificate(serviceSubject, validDays);
var clientCert = CertificateKeyManager.CreateDevelopmentCertificate(clientSubject, validDays);
var keyManager = new CertificateKeyManager(serviceCert, new[] { clientCert.Thumbprint });

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
        host.Credentials.ClientCertificate.Authentication.RevocationMode = X509RevocationMode.Online;

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

app.MapGet("/", () => "Health information exchange SOAP endpoint: /HealthRecords.svc (HTTPS, WS-Security mutual certificate, AES-256 + RSA-SHA256 suite).");

app.Run();
