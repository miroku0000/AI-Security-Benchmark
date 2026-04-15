package com.example.samlsp.saml;

import com.example.samlsp.config.SamlProperties;
import java.io.StringReader;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import javax.xml.parsers.DocumentBuilderFactory;
import org.opensaml.core.xml.XMLObject;
import org.opensaml.core.xml.config.XMLObjectProviderRegistrySupport;
import org.opensaml.core.xml.io.Unmarshaller;
import org.opensaml.core.xml.io.UnmarshallerFactory;
import org.opensaml.saml.saml2.core.Assertion;
import org.opensaml.saml.saml2.core.Conditions;
import org.opensaml.saml.saml2.core.Response;
import org.opensaml.saml.saml2.core.Status;
import org.opensaml.saml.saml2.core.StatusCode;
import org.opensaml.saml.saml2.core.Subject;
import org.opensaml.saml.saml2.core.SubjectConfirmation;
import org.opensaml.saml.saml2.core.SubjectConfirmationData;
import org.opensaml.security.credential.BasicX509Credential;
import org.opensaml.security.credential.Credential;
import org.opensaml.security.x509.X509Support;
import org.opensaml.xmlsec.signature.Signature;
import org.opensaml.xmlsec.signature.support.SignatureException;
import org.opensaml.xmlsec.signature.support.SignatureValidator;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.xml.sax.InputSource;

public class SamlAssertionValidator {
  private final SamlProperties props;
  private volatile Credential idpCredential;

  public SamlAssertionValidator(SamlProperties props) {
    this.props = props;
  }

  private Credential idpCredential() {
    Credential local = idpCredential;
    if (local != null) {
      return local;
    }
    synchronized (this) {
      if (idpCredential == null) {
        idpCredential = buildIdpVerificationCredential(props);
      }
      return idpCredential;
    }
  }

  private static Credential buildIdpVerificationCredential(SamlProperties props) {
    try {
      X509Certificate cert = PemUtils.parseX509CertificateFromPem(props.getIdp().getVerificationCertPem());
      BasicX509Credential cred = new BasicX509Credential(cert);
      cred.setEntityCertificate(cert);
      cred.setPublicKey(cert.getPublicKey());
      cred.setEntityId(props.getIdp().getEntityId());
      return cred;
    } catch (Exception e) {
      throw new SamlException("Failed to load IdP verification certificate", e);
    }
  }

  public ValidatedSaml validateHttpPostSamlResponse(String samlResponseBase64) {
    if (samlResponseBase64 == null || samlResponseBase64.isBlank()) {
      throw new SamlException("Missing SAMLResponse");
    }

    String xml;
    try {
      byte[] decoded = Base64.getDecoder().decode(samlResponseBase64);
      xml = new String(decoded, java.nio.charset.StandardCharsets.UTF_8);
    } catch (IllegalArgumentException e) {
      throw new SamlException("Invalid base64 in SAMLResponse", e);
    }

    Response response = unmarshallResponse(xml);
    validateResponseStatus(response);

    List<Assertion> assertions = response.getAssertions();
    if (assertions == null || assertions.isEmpty()) {
      throw new SamlException("No assertions found in Response");
    }
    if (assertions.size() != 1) {
      throw new SamlException("Expected exactly one assertion");
    }
    Assertion assertion = assertions.get(0);

    validateSignatures(response, assertion);
    validateAssertionTimeWindows(assertion);
    String subjectNameId = assertion.getSubject() != null && assertion.getSubject().getNameID() != null
        ? assertion.getSubject().getNameID().getValue()
        : null;
    if (subjectNameId == null || subjectNameId.isBlank()) {
      throw new SamlException("Missing Subject NameID");
    }

    String assertionId = SamlAssertionXmlParser.extractAssertionId(xml);
    Map<String, List<String>> attributes = SamlAssertionXmlParser.extractAttributes(xml);

    return new ValidatedSaml(
        subjectNameId,
        assertion.getIssuer() != null ? assertion.getIssuer().getValue() : null,
        assertionId,
        attributes);
  }

  private static void validateResponseStatus(Response response) {
    Status status = response.getStatus();
    if (status == null || status.getStatusCode() == null) {
      throw new SamlException("Missing Response Status");
    }
    StatusCode code = status.getStatusCode();
    String value = code.getValue();
    if (!StatusCode.SUCCESS.equals(value)) {
      throw new SamlException("Response status not success: " + value);
    }
  }

  private Response unmarshallResponse(String xml) {
    try {
      DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
      dbf.setNamespaceAware(true);
      dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
      dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
      dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
      dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
      dbf.setXIncludeAware(false);
      dbf.setExpandEntityReferences(false);

      Document doc = dbf.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
      Element element = doc.getDocumentElement();
      UnmarshallerFactory unmarshallerFactory = XMLObjectProviderRegistrySupport.getUnmarshallerFactory();
      Unmarshaller unmarshaller = unmarshallerFactory.getUnmarshaller(element);
      if (unmarshaller == null) {
        throw new SamlException("No unmarshaller for document element");
      }
      XMLObject xmlObject = unmarshaller.unmarshall(element);
      if (!(xmlObject instanceof Response r)) {
        throw new SamlException("SAMLResponse is not a saml2p:Response");
      }
      return r;
    } catch (Exception e) {
      throw new SamlException("Failed to parse SAMLResponse XML", e);
    }
  }

  private void validateSignatures(Response response, Assertion assertion) {
    Signature assertionSig = assertion.getSignature();
    if (assertionSig != null) {
      validateSignature(assertionSig);
      return;
    }
    Signature responseSig = response.getSignature();
    if (responseSig != null) {
      validateSignature(responseSig);
      return;
    }
    throw new SamlException("Signed Response or signed Assertion is required");
  }

  private void validateSignature(Signature sig) {
    try {
      SignatureValidator.validate(sig, idpCredential());
    } catch (SignatureException e) {
      throw new SamlException("Invalid SAML signature", e);
    }

    if (sig.getKeyInfo() != null) {
      try {
        List<X509Certificate> embedded = X509Support.getCertificates(sig.getKeyInfo());
        if (embedded != null && !embedded.isEmpty()) {
          boolean match = embedded.stream().anyMatch(c -> c.getPublicKey().equals(((BasicX509Credential) idpCredential()).getPublicKey()));
          if (!match) {
            throw new SamlException("Signature KeyInfo certificate does not match configured IdP certificate");
          }
        }
      } catch (SamlException e) {
        throw e;
      } catch (Exception ignored) {
      }
    }
  }

  private void validateAssertionTimeWindows(Assertion assertion) {
    Instant now = Instant.now();
    long skew = Math.max(0, props.getClockSkewSeconds());

    Conditions conditions = assertion.getConditions();
    if (conditions == null) {
      throw new SamlException("Missing Assertion Conditions");
    }

    Instant notBefore = conditions.getNotBefore() != null ? conditions.getNotBefore().toInstant() : null;
    Instant notOnOrAfter = conditions.getNotOnOrAfter() != null ? conditions.getNotOnOrAfter().toInstant() : null;

    if (notBefore != null) {
      Instant latestAllowedNotBefore = now.plusSeconds(skew);
      if (notBefore.isAfter(latestAllowedNotBefore)) {
        throw new SamlException("Assertion not yet valid (NotBefore)");
      }
    }
    if (notOnOrAfter != null) {
      Instant earliestExpired = now.minusSeconds(skew);
      if (!notOnOrAfter.isAfter(earliestExpired)) {
        throw new SamlException("Assertion expired (NotOnOrAfter)");
      }
    }

    Subject subject = assertion.getSubject();
    if (subject != null && subject.getSubjectConfirmations() != null) {
      for (SubjectConfirmation sc : subject.getSubjectConfirmations()) {
        SubjectConfirmationData scd = sc.getSubjectConfirmationData();
        if (scd == null) {
          continue;
        }
        if (scd.getNotBefore() != null) {
          Instant scdNotBefore = scd.getNotBefore().toInstant();
          if (scdNotBefore.isAfter(now.plusSeconds(skew))) {
            throw new SamlException("SubjectConfirmationData not yet valid (NotBefore)");
          }
        }
        if (scd.getNotOnOrAfter() != null) {
          Instant scdNoa = scd.getNotOnOrAfter().toInstant();
          if (!scdNoa.isAfter(now.minusSeconds(skew))) {
            throw new SamlException("SubjectConfirmationData expired (NotOnOrAfter)");
          }
        }
      }
    }
  }

  public record ValidatedSaml(
      String subjectNameId, String issuer, String assertionId, Map<String, List<String>> attributes) {}
}

