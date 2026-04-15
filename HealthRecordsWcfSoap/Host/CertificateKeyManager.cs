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
