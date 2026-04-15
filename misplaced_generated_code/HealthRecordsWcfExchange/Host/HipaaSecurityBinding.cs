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
            throw new SecurityTokenValidationException("Client X.509 certificate is required.");

        var thumb = NormalizeThumbprint(certificate.Thumbprint);
        if (!_trustedThumbprints.Contains(thumb))
            throw new SecurityTokenValidationException("Client certificate thumbprint is not trusted for this HIE endpoint.");
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
