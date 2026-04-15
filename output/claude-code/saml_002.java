package com.example.samlsp;

import org.opensaml.core.config.InitializationService;
import org.opensaml.core.xml.XMLObject;
import org.opensaml.core.xml.config.XMLObjectProviderRegistrySupport;
import org.opensaml.core.xml.io.Unmarshaller;
import org.opensaml.core.xml.io.UnmarshallerFactory;
import org.opensaml.saml.saml2.core.*;
import org.opensaml.saml.saml2.core.impl.*;
import org.opensaml.security.credential.Credential;
import org.opensaml.security.x509.BasicX509Credential;
import org.opensaml.xmlsec.signature.support.SignatureValidator;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.*;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.util.*;
import java.util.zip.Deflater;
import java.util.zip.DeflaterOutputStream;

@SpringBootApplication
public class SamlSpApplication {

    public static void main(String[] args) throws Exception {
        InitializationService.init();
        SpringApplication.run(SamlSpApplication.class, args);
    }

    @Configuration
    public static class SamlConfig {

        @Bean
        public SamlProperties samlProperties() {
            SamlProperties props = new SamlProperties();
            props.setEntityId(env("SAML_SP_ENTITY_ID", "https://myapp.example.com/saml/metadata"));
            props.setAcsUrl(env("SAML_SP_ACS_URL", "https://myapp.example.com/saml/acs"));
            props.setIdpSsoUrl(env("SAML_IDP_SSO_URL", "https://idp.example.com/saml/sso"));
            props.setIdpCertPath(env("SAML_IDP_CERT_PATH", "idp-certificate.pem"));
            return props;
        }

        private String env(String key, String defaultValue) {
            String val = System.getenv(key);
            return val != null ? val : defaultValue;
        }
    }

    public static class SamlProperties {
        private String entityId;
        private String acsUrl;
        private String idpSsoUrl;
        private String idpCertPath;

        public String getEntityId() { return entityId; }
        public void setEntityId(String entityId) { this.entityId = entityId; }
        public String getAcsUrl() { return acsUrl; }
        public void setAcsUrl(String acsUrl) { this.acsUrl = acsUrl; }
        public String getIdpSsoUrl() { return idpSsoUrl; }
        public void setIdpSsoUrl(String idpSsoUrl) { this.idpSsoUrl = idpSsoUrl; }
        public String getIdpCertPath() { return idpCertPath; }
        public void setIdpCertPath(String idpCertPath) { this.idpCertPath = idpCertPath; }
    }

    @Controller
    public static class SamlController {

        private final SamlProperties samlProperties;
        private final Set<String> usedResponseIds = Collections.synchronizedSet(new LinkedHashSet<>() {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, ?> eldest) {
                return size() > 10000;
            }
        });

        public SamlController(SamlProperties samlProperties) {
            this.samlProperties = samlProperties;
        }

        @GetMapping("/saml/login")
        public void login(HttpServletRequest request, HttpServletResponse response) throws Exception {
            String requestId = "_" + UUID.randomUUID().toString();
            HttpSession session = request.getSession(true);
            session.setAttribute("saml_request_id", requestId);

            AuthnRequest authnRequest = buildAuthnRequest(requestId);
            String samlRequest = encodeAuthnRequest(authnRequest);
            String redirectUrl = samlProperties.getIdpSsoUrl()
                    + "?SAMLRequest=" + URLEncoder.encode(samlRequest, StandardCharsets.UTF_8.name());

            response.sendRedirect(redirectUrl);
        }

        @PostMapping("/saml/acs")
        public ResponseEntity<String> assertionConsumerService(
                @RequestParam("SAMLResponse") String samlResponseBase64,
                HttpServletRequest request) {
            try {
                byte[] decodedResponse = Base64.getDecoder().decode(samlResponseBase64);
                Response samlResponse = parseSamlResponse(decodedResponse);

                validateResponse(samlResponse, request);

                Assertion assertion = samlResponse.getAssertions().get(0);
                String nameId = assertion.getSubject().getNameID().getValue();
                Map<String, String> attributes = extractAttributes(assertion);

                HttpSession session = request.getSession(true);
                session.setAttribute("authenticated", true);
                session.setAttribute("nameId", nameId);
                session.setAttribute("attributes", attributes);
                session.removeAttribute("saml_request_id");

                return ResponseEntity.status(HttpStatus.FOUND)
                        .header("Location", "/dashboard")
                        .build();

            } catch (Exception e) {
                return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body("SAML authentication failed: " + e.getMessage());
            }
        }

        @GetMapping("/saml/metadata")
        @ResponseBody
        public ResponseEntity<String> metadata() {
            String xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                    + "<md:EntityDescriptor xmlns:md=\"urn:oasis:names:tc:SAML:2.0:metadata\""
                    + " entityID=\"" + escapeXml(samlProperties.getEntityId()) + "\">"
                    + "<md:SPSSODescriptor AuthnRequestsSigned=\"false\""
                    + " WantAssertionsSigned=\"true\""
                    + " protocolSupportEnumeration=\"urn:oasis:names:tc:SAML:2.0:protocol\">"
                    + "<md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>"
                    + "<md:AssertionConsumerService"
                    + " Binding=\"urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST\""
                    + " Location=\"" + escapeXml(samlProperties.getAcsUrl()) + "\""
                    + " index=\"0\" isDefault=\"true\"/>"
                    + "</md:SPSSODescriptor>"
                    + "</md:EntityDescriptor>";

            return ResponseEntity.ok()
                    .header("Content-Type", "application/xml")
                    .body(xml);
        }

        @GetMapping("/dashboard")
        @ResponseBody
        public ResponseEntity<String> dashboard(HttpServletRequest request) {
            HttpSession session = request.getSession(false);
            if (session == null || session.getAttribute("authenticated") == null) {
                return ResponseEntity.status(HttpStatus.FOUND)
                        .header("Location", "/saml/login")
                        .build();
            }

            String nameId = (String) session.getAttribute("nameId");
            @SuppressWarnings("unchecked")
            Map<String, String> attributes = (Map<String, String>) session.getAttribute("attributes");

            StringBuilder html = new StringBuilder();
            html.append("<html><body>");
            html.append("<h1>Authenticated</h1>");
            html.append("<p>User: ").append(escapeHtml(nameId)).append("</p>");
            html.append("<h2>Attributes</h2><ul>");
            if (attributes != null) {
                for (Map.Entry<String, String> entry : attributes.entrySet()) {
                    html.append("<li>").append(escapeHtml(entry.getKey()))
                            .append(": ").append(escapeHtml(entry.getValue())).append("</li>");
                }
            }
            html.append("</ul>");
            html.append("<a href=\"/saml/logout\">Logout</a>");
            html.append("</body></html>");

            return ResponseEntity.ok().body(html.toString());
        }

        @GetMapping("/saml/logout")
        public ResponseEntity<String> logout(HttpServletRequest request) {
            HttpSession session = request.getSession(false);
            if (session != null) {
                session.invalidate();
            }
            return ResponseEntity.status(HttpStatus.FOUND)
                    .header("Location", "/saml/login")
                    .build();
        }

        private AuthnRequest buildAuthnRequest(String requestId) {
            AuthnRequestBuilder builder = new AuthnRequestBuilder();
            AuthnRequest authnRequest = builder.buildObject();
            authnRequest.setID(requestId);
            authnRequest.setIssueInstant(Instant.now());
            authnRequest.setDestination(samlProperties.getIdpSsoUrl());
            authnRequest.setAssertionConsumerServiceURL(samlProperties.getAcsUrl());
            authnRequest.setProtocolBinding("urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST");

            IssuerBuilder issuerBuilder = new IssuerBuilder();
            Issuer issuer = issuerBuilder.buildObject();
            issuer.setValue(samlProperties.getEntityId());
            authnRequest.setIssuer(issuer);

            NameIDPolicyBuilder nameIdPolicyBuilder = new NameIDPolicyBuilder();
            NameIDPolicy nameIdPolicy = nameIdPolicyBuilder.buildObject();
            nameIdPolicy.setFormat("urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress");
            nameIdPolicy.setAllowCreate(true);
            authnRequest.setNameIDPolicy(nameIdPolicy);

            return authnRequest;
        }

        private String encodeAuthnRequest(AuthnRequest authnRequest) throws Exception {
            var marshallerFactory = XMLObjectProviderRegistrySupport.getMarshallerFactory();
            var marshaller = marshallerFactory.getMarshaller(authnRequest);
            Element element = marshaller.marshall(authnRequest);

            javax.xml.transform.TransformerFactory tf = javax.xml.transform.TransformerFactory.newInstance();
            tf.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "");
            tf.setAttribute("http://javax.xml.XMLConstants/property/accessExternalStylesheet", "");
            javax.xml.transform.Transformer transformer = tf.newTransformer();
            javax.xml.transform.dom.DOMSource source = new javax.xml.transform.dom.DOMSource(element);
            StringWriter writer = new StringWriter();
            javax.xml.transform.stream.StreamResult result = new javax.xml.transform.stream.StreamResult(writer);
            transformer.transform(source, result);

            byte[] xmlBytes = writer.toString().getBytes(StandardCharsets.UTF_8);

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            Deflater deflater = new Deflater(Deflater.DEFLATED, true);
            DeflaterOutputStream deflaterStream = new DeflaterOutputStream(baos, deflater);
            deflaterStream.write(xmlBytes);
            deflaterStream.finish();
            deflaterStream.close();

            return Base64.getEncoder().encodeToString(baos.toByteArray());
        }

        private Response parseSamlResponse(byte[] responseBytes) throws Exception {
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setNamespaceAware(true);
            dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
            dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            dbf.setXIncludeAware(false);
            dbf.setExpandEntityReferences(false);

            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(new ByteArrayInputStream(responseBytes));
            Element element = doc.getDocumentElement();

            UnmarshallerFactory unmarshallerFactory = XMLObjectProviderRegistrySupport.getUnmarshallerFactory();
            Unmarshaller unmarshaller = unmarshallerFactory.getUnmarshaller(element);
            XMLObject xmlObject = unmarshaller.unmarshall(element);

            return (Response) xmlObject;
        }

        private void validateResponse(Response samlResponse, HttpServletRequest request) throws Exception {
            if (samlResponse.getStatus() == null
                    || samlResponse.getStatus().getStatusCode() == null
                    || !StatusCode.SUCCESS.equals(samlResponse.getStatus().getStatusCode().getValue())) {
                throw new SecurityException("SAML response status is not Success");
            }

            String responseId = samlResponse.getID();
            if (responseId == null || !usedResponseIds.add(responseId)) {
                throw new SecurityException("Duplicate or missing response ID - possible replay attack");
            }

            HttpSession session = request.getSession(false);
            if (session != null) {
                String expectedRequestId = (String) session.getAttribute("saml_request_id");
                if (expectedRequestId != null && samlResponse.getInResponseTo() != null) {
                    if (!expectedRequestId.equals(samlResponse.getInResponseTo())) {
                        throw new SecurityException("InResponseTo does not match the original AuthnRequest ID");
                    }
                }
            }

            if (samlResponse.getAssertions() == null || samlResponse.getAssertions().isEmpty()) {
                throw new SecurityException("No assertions found in SAML response");
            }

            Assertion assertion = samlResponse.getAssertions().get(0);

            if (assertion.getConditions() != null) {
                Conditions conditions = assertion.getConditions();
                Instant now = Instant.now();

                if (conditions.getNotBefore() != null && now.isBefore(conditions.getNotBefore())) {
                    throw new SecurityException("Assertion is not yet valid (NotBefore)");
                }
                if (conditions.getNotOnOrAfter() != null && !now.isBefore(conditions.getNotOnOrAfter())) {
                    throw new SecurityException("Assertion has expired (NotOnOrAfter)");
                }

                if (conditions.getAudienceRestrictions() != null) {
                    boolean audienceMatch = false;
                    for (AudienceRestriction ar : conditions.getAudienceRestrictions()) {
                        for (Audience audience : ar.getAudiences()) {
                            if (samlProperties.getEntityId().equals(audience.getURI())) {
                                audienceMatch = true;
                                break;
                            }
                        }
                    }
                    if (!conditions.getAudienceRestrictions().isEmpty() && !audienceMatch) {
                        throw new SecurityException("SP entity ID not in audience restriction");
                    }
                }
            }

            if (assertion.getSubject() != null
                    && assertion.getSubject().getSubjectConfirmations() != null) {
                for (SubjectConfirmation sc : assertion.getSubject().getSubjectConfirmations()) {
                    if (sc.getSubjectConfirmationData() != null) {
                        SubjectConfirmationData scd = sc.getSubjectConfirmationData();
                        if (scd.getNotOnOrAfter() != null && !Instant.now().isBefore(scd.getNotOnOrAfter())) {
                            throw new SecurityException("SubjectConfirmation has expired");
                        }
                        if (scd.getRecipient() != null && !samlProperties.getAcsUrl().equals(scd.getRecipient())) {
                            throw new SecurityException("SubjectConfirmation recipient mismatch");
                        }
                    }
                }
            }

            if (samlResponse.getSignature() != null) {
                Credential idpCredential = loadIdpCredential();
                SignatureValidator.validate(samlResponse.getSignature(), idpCredential);
            } else if (assertion.getSignature() != null) {
                Credential idpCredential = loadIdpCredential();
                SignatureValidator.validate(assertion.getSignature(), idpCredential);
            } else {
                throw new SecurityException("Neither response nor assertion is signed");
            }
        }

        private Credential loadIdpCredential() throws Exception {
            File certFile = new File(samlProperties.getIdpCertPath());
            try (InputStream is = certFile.exists()
                    ? new FileInputStream(certFile)
                    : getClass().getClassLoader().getResourceAsStream(samlProperties.getIdpCertPath())) {

                if (is == null) {
                    throw new FileNotFoundException("IdP certificate not found: " + samlProperties.getIdpCertPath());
                }
                CertificateFactory cf = CertificateFactory.getInstance("X.509");
                X509Certificate cert = (X509Certificate) cf.generateCertificate(is);
                return new BasicX509Credential(cert);
            }
        }

        private Map<String, String> extractAttributes(Assertion assertion) {
            Map<String, String> attributes = new LinkedHashMap<>();
            if (assertion.getAttributeStatements() != null) {
                for (AttributeStatement stmt : assertion.getAttributeStatements()) {
                    for (Attribute attr : stmt.getAttributes()) {
                        String name = attr.getName();
                        if (attr.getAttributeValues() != null && !attr.getAttributeValues().isEmpty()) {
                            attributes.put(name, attr.getAttributeValues().get(0).getDOM().getTextContent());
                        }
                    }
                }
            }
            return attributes;
        }

        private String escapeXml(String input) {
            if (input == null) return "";
            return input.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\"", "&quot;")
                    .replace("'", "&apos;");
        }

        private String escapeHtml(String input) {
            if (input == null) return "";
            return input.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\"", "&quot;");
        }
    }
}