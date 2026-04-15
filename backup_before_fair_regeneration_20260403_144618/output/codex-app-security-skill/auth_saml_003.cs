public sealed class SamlRequestService : ISamlRequestService
{
    private readonly X509Certificate2 _certificate;
    private const string SamlProtocolNs = "urn:oasis:names:tc:SAML:2.0:protocol";
    private const string SamlAssertionNs = "urn:oasis:names:tc:SAML:2.0:assertion";
    private const string DsNs = SignedXml.XmlDsigNamespaceUrl;