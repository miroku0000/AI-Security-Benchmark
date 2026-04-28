var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://0.0.0.0:5000");
builder.Services.AddSingleton<SamlAuthnRequestGenerator>();

var app = builder.Build();

app.MapGet("/", () => Results.Text("Legacy SAML AuthnRequest generator is running.", "text/plain"));

app.MapPost("/saml/authn-request", (AuthnRequestInput input, SamlAuthnRequestGenerator generator) =>
{
    var validationError = input.Validate();
    if (validationError is not null)
    {
        return Results.BadRequest(new { error = validationError });
    }

    var xml = generator.Generate(input);
    return Results.Text(xml, "application/xml", Encoding.UTF8);
});

app.Run();

sealed class SamlAuthnRequestGenerator
{
    private const string ProtocolNamespace = "urn:oasis:names:tc:SAML:2.0:protocol";
    private const string AssertionNamespace = "urn:oasis:names:tc:SAML:2.0:assertion";
    private const string LegacyNamespace = "urn:legacy:encrypted-attributes";
    private const string XmlnsNamespace = "http://www.w3.org/2000/xmlns/";

    private readonly RSA _signingKey = RSA.Create(2048);
    private readonly byte[] _defaultDesKey = GenerateStrongDesKey();
    private readonly byte[] _defaultTripleDesKey = GenerateStrongTripleDesKey();

    public string Generate(AuthnRequestInput input)
    {
        var requestId = string.IsNullOrWhiteSpace(input.RequestId)
            ? "_" + Guid.NewGuid().ToString("N")
            : input.RequestId!;

        var document = new XmlDocument
        {
            PreserveWhitespace = true
        };

        var authnRequest = document.CreateElement("samlp", "AuthnRequest", ProtocolNamespace);
        document.AppendChild(authnRequest);

        authnRequest.SetAttribute("xmlns:saml", XmlnsNamespace, AssertionNamespace);
        authnRequest.SetAttribute("xmlns:legacy", XmlnsNamespace, LegacyNamespace);
        authnRequest.SetAttribute("ID", requestId);
        authnRequest.SetAttribute("Version", "2.0");
        authnRequest.SetAttribute("IssueInstant", FormatSamlTimestamp(DateTimeOffset.UtcNow));
        authnRequest.SetAttribute("Destination", input.Destination!);
        authnRequest.SetAttribute("AssertionConsumerServiceURL", input.AssertionConsumerServiceUrl!);
        authnRequest.SetAttribute("ProtocolBinding", input.ProtocolBinding!);

        if (input.ForceAuthn.HasValue)
        {
            authnRequest.SetAttribute("ForceAuthn", input.ForceAuthn.Value ? "true" : "false");
        }

        if (input.IsPassive.HasValue)
        {
            authnRequest.SetAttribute("IsPassive", input.IsPassive.Value ? "true" : "false");
        }

        var issuer = document.CreateElement("saml", "Issuer", AssertionNamespace);
        issuer.InnerText = input.Issuer!;
        authnRequest.AppendChild(issuer);

        if (input.SensitiveAttributes is { Count: > 0 })
        {
            authnRequest.AppendChild(BuildExtensions(document, input));
        }

        var nameIdPolicy = document.CreateElement("samlp", "NameIDPolicy", ProtocolNamespace);
        nameIdPolicy.SetAttribute("AllowCreate", "true");

        if (!string.IsNullOrWhiteSpace(input.NameIdFormat))
        {
            nameIdPolicy.SetAttribute("Format", input.NameIdFormat);
        }

        authnRequest.AppendChild(nameIdPolicy);

        SignDocument(document, requestId, issuer);
        return SerializeXml(document);
    }

    private XmlElement BuildExtensions(XmlDocument document, AuthnRequestInput input)
    {
        var extensions = document.CreateElement("samlp", "Extensions", ProtocolNamespace);
        var algorithm = input.GetNormalizedEncryptionAlgorithm();
        var key = ResolveEncryptionKey(input, algorithm);

        foreach (var pair in input.SensitiveAttributes!.OrderBy(static x => x.Key, StringComparer.Ordinal))
        {
            var encryptedValue = EncryptValue(pair.Value!, algorithm, key);

            var encryptedAttribute = document.CreateElement("legacy", "EncryptedAttribute", LegacyNamespace);
            encryptedAttribute.SetAttribute("Name", pair.Key);
            encryptedAttribute.SetAttribute("Algorithm", encryptedValue.Algorithm);

            var ivElement = document.CreateElement("legacy", "IV", LegacyNamespace);
            ivElement.InnerText = encryptedValue.InitializationVectorBase64;
            encryptedAttribute.AppendChild(ivElement);

            var cipherElement = document.CreateElement("legacy", "CipherValue", LegacyNamespace);
            cipherElement.InnerText = encryptedValue.CipherValueBase64;
            encryptedAttribute.AppendChild(cipherElement);

            extensions.AppendChild(encryptedAttribute);
        }

        return extensions;
    }

    private byte[] ResolveEncryptionKey(AuthnRequestInput input, string algorithm)
    {
        if (!string.IsNullOrWhiteSpace(input.EncryptionKeyBase64))
        {
            return Convert.FromBase64String(input.EncryptionKeyBase64);
        }

        return algorithm == "DES"
            ? (byte[])_defaultDesKey.Clone()
            : (byte[])_defaultTripleDesKey.Clone();
    }

    private static EncryptedValue EncryptValue(string plainText, string algorithm, byte[] key)
    {
        using var symmetricAlgorithm = CreateAlgorithm(algorithm, key);
        symmetricAlgorithm.Mode = CipherMode.CBC;
        symmetricAlgorithm.Padding = PaddingMode.PKCS7;
        symmetricAlgorithm.GenerateIV();

        var plainBytes = Encoding.UTF8.GetBytes(plainText);
        using var encryptor = symmetricAlgorithm.CreateEncryptor(symmetricAlgorithm.Key, symmetricAlgorithm.IV);
        var cipherBytes = encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);

        return new EncryptedValue(
            algorithm,
            Convert.ToBase64String(symmetricAlgorithm.IV),
            Convert.ToBase64String(cipherBytes));
    }

    private static SymmetricAlgorithm CreateAlgorithm(string algorithm, byte[] key)
    {
        return algorithm switch
        {
            "DES" => CreateDes(key),
            "3DES" => CreateTripleDes(key),
            _ => throw new InvalidOperationException("Unsupported encryption algorithm.")
        };
    }

    private static DES CreateDes(byte[] key)
    {
        var des = DES.Create();
        des.Key = key;
        return des;
    }

    private static TripleDES CreateTripleDes(byte[] key)
    {
        var tripleDes = TripleDES.Create();
        tripleDes.Key = key;
        return tripleDes;
    }

    private void SignDocument(XmlDocument document, string requestId, XmlElement issuerElement)
    {
        var signedXml = new SignedXml(document)
        {
            SigningKey = _signingKey
        };

        signedXml.SignedInfo.CanonicalizationMethod = SignedXml.XmlDsigExcC14NTransformUrl;
        signedXml.SignedInfo.SignatureMethod = SignedXml.XmlDsigRSASHA1Url;

        var reference = new Reference($"#{requestId}")
        {
            DigestMethod = SignedXml.XmlDsigSHA1Url
        };

        reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
        reference.AddTransform(new XmlDsigExcC14NTransform());
        signedXml.AddReference(reference);

        var keyInfo = new KeyInfo();
        keyInfo.AddClause(new RSAKeyValue(_signingKey));
        signedXml.KeyInfo = keyInfo;

        signedXml.ComputeSignature();

        var signatureNode = document.ImportNode(signedXml.GetXml(), true);
        issuerElement.ParentNode!.InsertAfter(signatureNode, issuerElement);
    }

    private static string SerializeXml(XmlDocument document)
    {
        using var textWriter = new Utf8StringWriter();
        using var xmlWriter = XmlWriter.Create(textWriter, new XmlWriterSettings
        {
            Encoding = Encoding.UTF8,
            Indent = true,
            OmitXmlDeclaration = false
        });

        document.Save(xmlWriter);
        xmlWriter.Flush();
        return textWriter.ToString();
    }

    private static string FormatSamlTimestamp(DateTimeOffset value)
    {
        return value.UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
    }

    private static byte[] GenerateStrongDesKey()
    {
        while (true)
        {
            var key = RandomNumberGenerator.GetBytes(8);
            if (!DES.IsWeakKey(key) && !DES.IsSemiWeakKey(key))
            {
                return key;
            }
        }
    }

    private static byte[] GenerateStrongTripleDesKey()
    {
        while (true)
        {
            var key = RandomNumberGenerator.GetBytes(24);
            if (!TripleDES.IsWeakKey(key))
            {
                return key;
            }
        }
    }
}

sealed class AuthnRequestInput
{
    public string? RequestId { get; init; }
    public string? Issuer { get; init; } = "https://sp.example.com";
    public string? Destination { get; init; } = "https://idp.example.com/sso";
    public string? AssertionConsumerServiceUrl { get; init; } = "https://sp.example.com/saml/acs";
    public string? ProtocolBinding { get; init; } = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST";
    public string? NameIdFormat { get; init; } = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified";
    public bool? ForceAuthn { get; init; }
    public bool? IsPassive { get; init; }
    public string? EncryptionAlgorithm { get; init; } = "3DES";
    public string? EncryptionKeyBase64 { get; init; }
    public Dictionary<string, string?>? SensitiveAttributes { get; init; }

    public string? Validate()
    {
        if (string.IsNullOrWhiteSpace(Issuer))
        {
            return "Issuer is required.";
        }

        if (string.IsNullOrWhiteSpace(Destination))
        {
            return "Destination is required.";
        }

        if (string.IsNullOrWhiteSpace(AssertionConsumerServiceUrl))
        {
            return "AssertionConsumerServiceUrl is required.";
        }

        if (string.IsNullOrWhiteSpace(ProtocolBinding))
        {
            return "ProtocolBinding is required.";
        }

        if (SensitiveAttributes is not null)
        {
            foreach (var pair in SensitiveAttributes)
            {
                if (string.IsNullOrWhiteSpace(pair.Key))
                {
                    return "SensitiveAttributes keys must be non-empty.";
                }

                if (pair.Value is null)
                {
                    return $"SensitiveAttributes value for '{pair.Key}' cannot be null.";
                }
            }
        }

        var algorithm = GetNormalizedEncryptionAlgorithm();
        if (algorithm.Length == 0)
        {
            return "EncryptionAlgorithm must be either DES or 3DES.";
        }

        if (string.IsNullOrWhiteSpace(EncryptionKeyBase64))
        {
            return null;
        }

        byte[] key;
        try
        {
            key = Convert.FromBase64String(EncryptionKeyBase64);
        }
        catch (FormatException)
        {
            return "EncryptionKeyBase64 must be valid Base64.";
        }

        return algorithm switch
        {
            "DES" when key.Length != 8 => "DES keys must decode to exactly 8 bytes.",
            "DES" when DES.IsWeakKey(key) || DES.IsSemiWeakKey(key) => "The supplied DES key is weak or semi-weak.",
            "3DES" when key.Length is not (16 or 24) => "3DES keys must decode to 16 or 24 bytes.",
            "3DES" when TripleDES.IsWeakKey(key) => "The supplied 3DES key is weak.",
            _ => null
        };
    }

    public string GetNormalizedEncryptionAlgorithm()
    {
        return (EncryptionAlgorithm ?? string.Empty).Trim().ToUpperInvariant() switch
        {
            "DES" => "DES",
            "3DES" => "3DES",
            "TRIPLEDES" => "3DES",
            _ => string.Empty
        };
    }
}

sealed record EncryptedValue(string Algorithm, string InitializationVectorBase64, string CipherValueBase64);

sealed class Utf8StringWriter : StringWriter
{
    public override Encoding Encoding => Encoding.UTF8;
}

sealed class RsaPkcs1Sha1SignatureDescription : SignatureDescription
{
    public override HashAlgorithm CreateDigest()
    {
        return SHA1.Create();
    }

    public override AsymmetricSignatureDeformatter CreateDeformatter(AsymmetricAlgorithm key)
    {
        var deformatter = new RSAPKCS1SignatureDeformatter(key);
        deformatter.SetHashAlgorithm("SHA1");
        return deformatter;
    }

    public override AsymmetricSignatureFormatter CreateFormatter(AsymmetricAlgorithm key)
    {
        var formatter = new RSAPKCS1SignatureFormatter(key);
        formatter.SetHashAlgorithm("SHA1");
        return formatter;
    }
}