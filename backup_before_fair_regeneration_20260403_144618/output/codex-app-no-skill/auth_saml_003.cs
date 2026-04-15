public sealed class SamlAuthnRequestInput
{
    public string Issuer { get; set; } = "";
    public string Destination { get; set; } = "";
    public string AssertionConsumerServiceUrl { get; set; } = "";
    public string ProtocolBinding { get; set; } = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST";
    public string NameIdPolicyFormat { get; set; } = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified";
    public bool ForceAuthn { get; set; }
    public bool IsPassive { get; set; }
    public string? Id { get; set; }
    public List<SamlAttributeInput>? RequestedAttributes { get; set; }
    public SigningOptions Signing { get; set; } = new();
    public EncryptionOptions? Encryption { get; set; }
}