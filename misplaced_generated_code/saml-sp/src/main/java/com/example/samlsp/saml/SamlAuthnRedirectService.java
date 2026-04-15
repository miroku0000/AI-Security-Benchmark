package com.example.samlsp.saml;

import com.example.samlsp.config.SamlProperties;
import java.io.ByteArrayOutputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.UUID;
import java.util.zip.Deflater;
import java.util.zip.DeflaterOutputStream;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.opensaml.core.xml.XMLObject;
import org.opensaml.core.xml.config.XMLObjectProviderRegistrySupport;
import org.opensaml.core.xml.io.Marshaller;
import org.opensaml.saml.common.SAMLVersion;
import org.opensaml.saml.common.xml.SAMLConstants;
import org.opensaml.saml.saml2.core.AuthnRequest;
import org.opensaml.saml.saml2.core.impl.AuthnRequestBuilder;
import org.opensaml.saml.saml2.core.impl.IssuerBuilder;
import org.opensaml.saml.saml2.core.NameIDType;
import org.opensaml.saml.saml2.core.impl.NameIDPolicyBuilder;
import org.springframework.stereotype.Service;
import org.w3c.dom.Element;

@Service
public class SamlAuthnRedirectService {
  private final SamlProperties props;

  public SamlAuthnRedirectService(SamlProperties props) {
    this.props = props;
  }

  public String buildRedirectUrl(String relayState) {
    String sso = props.getIdp().getSsoUrl();
    if (sso == null || sso.isBlank()) {
      throw new SamlException("Missing saml.idp.ssoUrl");
    }
    String entityId = props.getSp().getEntityId();
    String acs = props.getSp().getAcsUrl();
    if (entityId == null || entityId.isBlank() || acs == null || acs.isBlank()) {
      throw new SamlException("Missing saml.sp.entityId or saml.sp.acsUrl");
    }

    AuthnRequest request = new AuthnRequestBuilder().buildObject();
    request.setID("_" + UUID.randomUUID().toString().replace("-", ""));
    request.setVersion(SAMLVersion.VERSION_20);
    request.setIssueInstant(java.time.Instant.now());
    request.setDestination(sso.trim());
    request.setProtocolBinding(SAMLConstants.SAML2_POST_BINDING_URI);
    request.setAssertionConsumerServiceURL(acs.trim());

    var issuer = new IssuerBuilder().buildObject();
    issuer.setValue(entityId.trim());
    request.setIssuer(issuer);

    var nameIdPolicy = new NameIDPolicyBuilder().buildObject();
    nameIdPolicy.setAllowCreate(true);
    nameIdPolicy.setFormat(NameIDType.EMAIL);
    request.setNameIDPolicy(nameIdPolicy);

    try {
      String xml = serializeXml(request);
      String encoded = base64Deflate(xml);
      StringBuilder url = new StringBuilder(sso.trim());
      url.append(sso.contains("?") ? "&" : "?");
      url.append("SAMLRequest=").append(urlEncode(encoded));
      if (relayState != null && !relayState.isBlank()) {
        url.append("&RelayState=").append(urlEncode(relayState.trim()));
      }
      return url.toString();
    } catch (Exception e) {
      throw new SamlException("Failed to build SAML redirect", e);
    }
  }

  private static String serializeXml(XMLObject object) throws Exception {
    Marshaller marshaller =
        XMLObjectProviderRegistrySupport.getMarshallerFactory().getMarshaller(object);
    if (marshaller == null) {
      throw new SamlException("No marshaller for AuthnRequest");
    }
    Element element = marshaller.marshall(object);
    TransformerFactory tf = TransformerFactory.newInstance();
    tf.setFeature(javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING, true);
    var transformer = tf.newTransformer();
    transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
    var out = new java.io.StringWriter();
    transformer.transform(new DOMSource(element), new StreamResult(out));
    return out.toString();
  }

  private static String base64Deflate(String xml) throws Exception {
    byte[] raw = xml.getBytes(StandardCharsets.UTF_8);
    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    try (DeflaterOutputStream def =
        new DeflaterOutputStream(bytes, new Deflater(Deflater.DEFLATED, true))) {
      def.write(raw);
    }
    return Base64.getEncoder().encodeToString(bytes.toByteArray());
  }

  private static String urlEncode(String s) {
    return URLEncoder.encode(s, StandardCharsets.UTF_8);
  }
}
