using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography.Xml;
using System.Text;
using System.Xml;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<SamlAuthnRequestService>();

var app = builder.Build();

app.MapPost("/saml/authn-request", (SamlRequestDto dto, SamlAuthnRequestService svc) =>
{
    try
    {
        var xml = svc.BuildSignedAuthnRequest(dto);
        return Results.Text(xml, "application/xml");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

app.MapGet("/", () => "POST /saml/authn-request with JSON body.");

app.Run();

internal sealed record SamlRequestDto
{
    public string Issuer { get; init; } = "";
    public string Destination { get; init; } = "";
    public string AcsUrl { get; init; } = "";
    public string ProviderName { get; init; } = "";
    public IReadOnlyList<SamlAttributeDto>? SensitiveAttributes { get; init; }
    public string? TripleDesKeyBase64 { get; init; }
    public bool Use3Des { get; init; } = true;
}

internal sealed record SamlAttributeDto
{
    public string Name { get; init; } = "";
    public string Format { get; init; } = "urn:oasis:names:tc:SAML:2.0:attrname-format:basic";
    public string Value { get; init; } = "";
    public string NameFormat { get; init; } = "urn:oasis:names:tc:SAML:2.0:attrname-format:basic";
}

internal sealed class SamlSignedXml : SignedXml
{
    public SamlSignedXml(XmlDocument xml) : base(xml) { }

    public override XmlElement? GetIdElement(XmlDocument document, string idValue)
    {
        var e = base.GetIdElement(document, idValue);
        if (e != null) return e;
        if (idValue.Contains('\'') || idValue.Contains('"')) return null;
        return document.SelectSingleNode($"//*[@ID='{idValue}']") as XmlElement;
    }
}

internal sealed class SamlAuthnRequestService
{
    private readonly IConfiguration _cfg;
    private readonly IWebHostEnvironment _env;

    public SamlAuthnRequestService(IConfiguration cfg, IWebHostEnvironment env)
    {
        _cfg = cfg;
        _env = env;
    }

    public string BuildSignedAuthnRequest(SamlRequestDto dto)
    {
        RegisterRsaSha1ForSignedXml();

        var rsa = LoadRsaFromPem(GetPrivateKeyPem());
        var cert = LoadCertificateIfPresent();

        var id = "_" + Guid.NewGuid().ToString("N");
        var issueInstant = DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", System.Globalization.CultureInfo.InvariantCulture);

        var doc = new XmlDocument { PreserveWhitespace = true };
        var decl = doc.CreateXmlDeclaration("1.0", "UTF-8", null);
        doc.AppendChild(decl);

        var authnNs = "urn:oasis:names:tc:SAML:2.0:protocol";
        var samlNs = "urn:oasis:names:tc:SAML:2.0:assertion";

        var authnRequest = doc.CreateElement("AuthnRequest", authnNs);
        authnRequest.Prefix = "samlp";
        authnRequest.SetAttribute("xmlns:samlp", authnNs);
        authnRequest.SetAttribute("xmlns:saml", samlNs);
        authnRequest.SetAttribute("ID", id);
        authnRequest.SetAttribute("Version", "2.0");
        authnRequest.SetAttribute("IssueInstant", issueInstant);
        authnRequest.SetAttribute("Destination", dto.Destination);
        authnRequest.SetAttribute("AssertionConsumerServiceURL", dto.AcsUrl);
        authnRequest.SetAttribute("ProtocolBinding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST");
        if (!string.IsNullOrEmpty(dto.ProviderName))
            authnRequest.SetAttribute("ProviderName", dto.ProviderName);

        var issuer = doc.CreateElement("Issuer", samlNs);
        issuer.Prefix = "saml";
        issuer.InnerText = dto.Issuer;
        authnRequest.AppendChild(issuer);

        var keyMaterial = ResolveTripleDesKey(dto.TripleDesKeyBase64);

        if (dto.SensitiveAttributes is { Count: > 0 })
        {
            var ext = doc.CreateElement("Extensions", authnNs);
            ext.Prefix = "samlp";
            var attrStatement = doc.CreateElement("AttributeStatement", samlNs);
            attrStatement.Prefix = "saml";
            foreach (var a in dto.SensitiveAttributes)
            {
                var attr = doc.CreateElement("Attribute", samlNs);
                attr.Prefix = "saml";
                attr.SetAttribute("Name", a.Name);
                attr.SetAttribute("NameFormat", string.IsNullOrEmpty(a.NameFormat) ? a.Format : a.NameFormat);
                var encVal = dto.Use3Des
                    ? TripleDesHelper.EncryptToBase64(a.Value, keyMaterial)
                    : DesHelper.EncryptToBase64(a.Value, keyMaterial);
                var val = doc.CreateElement("AttributeValue", samlNs);
                val.Prefix = "saml";
                val.InnerText = encVal;
                val.SetAttribute("Encryption", dto.Use3Des ? "urn:legacy:tripledes-cbc" : "urn:legacy:des-cbc");
                attr.AppendChild(val);
                attrStatement.AppendChild(attr);
            }
            ext.AppendChild(attrStatement);
            authnRequest.AppendChild(ext);
        }

        doc.AppendChild(authnRequest);

        using (rsa)
        {
            var signedXml = new SamlSignedXml(doc)
            {
                SigningKey = rsa
            };

            signedXml.SignedInfo.SignatureMethod = SignedXml.XmlDsigRSASHA1Url;
            var reference = new Reference { Uri = "#" + id };
            reference.DigestMethod = SignedXml.XmlDsigSHA1Url;
            reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
            reference.AddTransform(new XmlDsigExcC14NTransform());
            signedXml.AddReference(reference);

            if (cert != null)
            {
                var ki = new KeyInfo();
                ki.AddClause(new KeyInfoX509Data(cert));
                signedXml.KeyInfo = ki;
            }

            signedXml.ComputeSignature();
            var sigEl = signedXml.GetXml();
            authnRequest.AppendChild(doc.ImportNode(sigEl, true));
        }

        var sb = new StringBuilder();
        using (var sw = new StringWriter(sb))
        using (var xw = XmlWriter.Create(sw, new XmlWriterSettings { OmitXmlDeclaration = false, Indent = true, Encoding = new UTF8Encoding(false) }))
        {
            doc.WriteTo(xw);
        }
        return sb.ToString();
    }

    private static void RegisterRsaSha1ForSignedXml()
    {
        CryptoConfig.AddAlgorithm(typeof(RSAPKCS1SHA1SignatureDescription), SignedXml.XmlDsigRSASHA1Url);
    }

    private string GetPrivateKeyPem()
    {
        var path = _cfg["Saml:SigningKeyPemPath"];
        if (!string.IsNullOrEmpty(path))
        {
            var full = Path.IsPathRooted(path) ? path : Path.Combine(_env.ContentRootPath, path);
            if (File.Exists(full))
                return File.ReadAllText(full);
        }
        var inline = _cfg["Saml:SigningKeyPem"];
        if (!string.IsNullOrEmpty(inline))
            return inline;
        if (_env.IsDevelopment())
            return DevelopmentSigningKey.Pem;
        throw new InvalidOperationException("Configure Saml:SigningKeyPemPath or Saml:SigningKeyPem.");
    }

    private string? GetCertificatePemPath() => _cfg["Saml:SigningCertificatePemPath"];

    private X509Certificate2? LoadCertificateIfPresent()
    {
        var path = GetCertificatePemPath();
        if (string.IsNullOrEmpty(path)) return null;
        var full = Path.IsPathRooted(path) ? path : Path.Combine(_env.ContentRootPath, path);
        if (!File.Exists(full)) return null;
        return X509Certificate2.CreateFromPemFile(full);
    }

    private static RSA LoadRsaFromPem(string pem)
    {
        var rsa = RSA.Create();
        rsa.ImportFromPem(pem);
        return rsa;
    }

    private static byte[] ResolveTripleDesKey(string? base64Override)
    {
        if (!string.IsNullOrEmpty(base64Override))
        {
            var k = Convert.FromBase64String(base64Override);
            if (k.Length is 8 or 16 or 24)
                return k.Length == 8 ? PadDesTo3Des(k) : k;
            throw new InvalidOperationException("TripleDes key must be 8 (DES), 16, or 24 bytes base64.");
        }
        var key = new byte[24];
        RandomNumberGenerator.Fill(key);
        return key;
    }

    private static byte[] PadDesTo3Des(byte[] des8)
    {
        var t = new byte[24];
        Buffer.BlockCopy(des8, 0, t, 0, 8);
        Buffer.BlockCopy(des8, 0, t, 8, 8);
        Buffer.BlockCopy(des8, 0, t, 16, 8);
        return t;
    }
}

internal static class TripleDesHelper
{
    public static string EncryptToBase64(string plain, byte[] key24)
    {
        var plainBytes = Encoding.UTF8.GetBytes(plain);
        using var tdes = TripleDES.Create();
        tdes.Key = Normalize3DesKey(key24);
        tdes.Mode = CipherMode.CBC;
        tdes.Padding = PaddingMode.PKCS7;
        tdes.GenerateIV();
        using var enc = tdes.CreateEncryptor();
        var cipher = enc.TransformFinalBlock(plainBytes, 0, plainBytes.Length);
        var payload = new byte[tdes.IV.Length + cipher.Length];
        Buffer.BlockCopy(tdes.IV, 0, payload, 0, tdes.IV.Length);
        Buffer.BlockCopy(cipher, 0, payload, tdes.IV.Length, cipher.Length);
        return Convert.ToBase64String(payload);
    }

    private static byte[] Normalize3DesKey(byte[] key)
    {
        return key.Length switch
        {
            24 => key,
            16 => key,
            _ => throw new ArgumentException("3DES key must be 16 or 24 bytes.", nameof(key))
        };
    }
}

internal static class DevelopmentSigningKey
{
    private static readonly Lazy<string> PemLazy = new(() =>
    {
        using var rsa = RSA.Create(2048);
        return rsa.ExportPkcs8PrivateKeyPem();
    });

    public static string Pem => PemLazy.Value;
}

internal static class DesHelper
{
    public static string EncryptToBase64(string plain, byte[] keyMaterial)
    {
        var key8 = keyMaterial.Length >= 8 ? keyMaterial.AsSpan(0, 8).ToArray() : throw new ArgumentException("Need at least 8 bytes for DES key.");
        var plainBytes = Encoding.UTF8.GetBytes(plain);
        using var des = DES.Create();
        des.Key = key8;
        des.Mode = CipherMode.CBC;
        des.Padding = PaddingMode.PKCS7;
        des.GenerateIV();
        using var enc = des.CreateEncryptor();
        var cipher = enc.TransformFinalBlock(plainBytes, 0, plainBytes.Length);
        var payload = new byte[des.IV.Length + cipher.Length];
        Buffer.BlockCopy(des.IV, 0, payload, 0, des.IV.Length);
        Buffer.BlockCopy(cipher, 0, payload, des.IV.Length, cipher.Length);
        return Convert.ToBase64String(payload);
    }
}
