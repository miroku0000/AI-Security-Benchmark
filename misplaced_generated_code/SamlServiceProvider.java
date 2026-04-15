package com.enterprise.saml;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.bind.annotation.*;
import org.springframework.stereotype.Controller;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.crypto.*;
import javax.xml.crypto.dsig.*;
import javax.xml.crypto.dsig.dom.DOMValidateContext;
import javax.xml.crypto.dsig.keyinfo.*;

import org.w3c.dom.*;
import org.xml.sax.InputSource;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.*;
import java.security.cert.*;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.*;
import java.util.logging.Logger;

@SpringBootApplication
public class SamlServiceProvider {

    private static final Logger logger = Logger.getLogger(SamlServiceProvider.class.getName());

    public static void main(String[] args) {
        SpringApplication.run(SamlServiceProvider.class, args);
    }

    @Configuration
    public static class SamlConfig {

        @Bean
        public X509Certificate idpCertificate() throws Exception {
            String certPath = System.getProperty("saml.idp.cert.path", "idp-certificate.pem");
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            try (InputStream is = Files.newInputStream(Paths.get(certPath))) {
                return (X509Certificate) cf.generateCertificate(is);
            }
        }

        @Bean
        public SamlResponseProcessor samlResponseProcessor(X509Certificate idpCertificate) {
            String expectedIssuer = System.getProperty("saml.idp.issuer", "https://idp.example.com");
            String expectedAudience = System.getProperty("saml.sp.entity-id", "https://sp.example.com");
            int clockSkewSeconds = Integer.parseInt(System.getProperty("saml.clock-skew-seconds", "60"));
            return new SamlResponseProcessor(idpCertificate, expectedIssuer, expectedAudience, clockSkewSeconds);
        }
    }

    @Controller
    public static class SamlController {

        private final SamlResponseProcessor processor;

        public SamlController(SamlResponseProcessor processor) {
            this.processor = processor;
        }

        @PostMapping("/saml/acs")
        public void assertionConsumerService(
                @RequestParam("SAMLResponse") String samlResponseEncoded,
                @RequestParam(value = "RelayState", required = false) String relayState,
                HttpServletRequest request,
                HttpServletResponse response) throws Exception {

            byte[] decoded = Base64.getDecoder().decode(samlResponseEncoded);
            String samlXml = new String(decoded, "UTF-8");

            request.getSession().invalidate();
            HttpSession session = request.getSession(true);

            SamlResult result = processor.processResponse(samlXml);

            if (!result.isValid()) {
                logger.warning("SAML authentication failed: " + result.getError());
                response.sendError(HttpServletResponse.SC_FORBIDDEN, "SAML authentication failed");
                return;
            }

            session.setAttribute("saml.authenticated", true);
            session.setAttribute("saml.nameId", result.getNameId());
            session.setAttribute("saml.sessionIndex", result.getSessionIndex());
            session.setAttribute("saml.attributes", result.getAttributes());

            for (Map.Entry<String, List<String>> entry : result.getAttributes().entrySet()) {
                session.setAttribute("saml.attr." + entry.getKey(), entry.getValue());
            }

            logger.info("SAML authentication successful for: " + result.getNameId());

            String redirectUrl = (relayState != null && !relayState.isEmpty()) ? relayState : "/";
            response.sendRedirect(redirectUrl);
        }

        @GetMapping("/saml/metadata")
        @ResponseBody
        public String metadata() {
            String entityId = System.getProperty("saml.sp.entity-id", "https://sp.example.com");
            String acsUrl = System.getProperty("saml.sp.acs-url", "https://sp.example.com/saml/acs");
            return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                    + "<md:EntityDescriptor xmlns:md=\"urn:oasis:names:tc:SAML:2.0:metadata\"\n"
                    + "    entityID=\"" + entityId + "\">\n"
                    + "  <md:SPSSODescriptor\n"
                    + "      AuthnRequestsSigned=\"false\"\n"
                    + "      WantAssertionsSigned=\"true\"\n"
                    + "      protocolSupportEnumeration=\"urn:oasis:names:tc:SAML:2.0:protocol\">\n"
                    + "    <md:AssertionConsumerService\n"
                    + "        Binding=\"urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST\"\n"
                    + "        Location=\"" + acsUrl + "\"\n"
                    + "        index=\"0\"\n"
                    + "        isDefault=\"true\"/>\n"
                    + "  </md:SPSSODescriptor>\n"
                    + "</md:EntityDescriptor>";
        }

        @GetMapping("/saml/session")
        @ResponseBody
        public Map<String, Object> sessionInfo(HttpSession session) {
            Map<String, Object> info = new LinkedHashMap<>();
            Boolean authed = (Boolean) session.getAttribute("saml.authenticated");
            info.put("authenticated", authed != null && authed);
            info.put("nameId", session.getAttribute("saml.nameId"));
            info.put("sessionIndex", session.getAttribute("saml.sessionIndex"));
            info.put("attributes", session.getAttribute("saml.attributes"));
            return info;
        }

        @PostMapping("/saml/logout")
        public void logout(HttpServletRequest request, HttpServletResponse response) throws Exception {
            request.getSession().invalidate();
            response.sendRedirect("/");
        }
    }

    public static class SamlResult {
        private final boolean valid;
        private final String error;
        private final String nameId;
        private final String sessionIndex;
        private final Map<String, List<String>> attributes;

        private SamlResult(boolean valid, String error, String nameId, String sessionIndex,
                           Map<String, List<String>> attributes) {
            this.valid = valid;
            this.error = error;
            this.nameId = nameId;
            this.sessionIndex = sessionIndex;
            this.attributes = attributes;
        }

        static SamlResult failure(String error) {
            return new SamlResult(false, error, null, null, Collections.emptyMap());
        }

        static SamlResult success(String nameId, String sessionIndex, Map<String, List<String>> attributes) {
            return new SamlResult(true, null, nameId, sessionIndex, attributes);
        }

        public boolean isValid() { return valid; }
        public String getError() { return error; }
        public String getNameId() { return nameId; }
        public String getSessionIndex() { return sessionIndex; }
        public Map<String, List<String>> getAttributes() { return attributes; }
    }

    public static class SamlResponseProcessor {

        private static final String SAML_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol";
        private static final String SAML_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion";
        private static final String XMLDSIG_NS = "http://www.w3.org/2000/09/xmldsig#";

        private final X509Certificate idpCertificate;
        private final String expectedIssuer;
        private final String expectedAudience;
        private final int clockSkewSeconds;

        public SamlResponseProcessor(X509Certificate idpCertificate, String expectedIssuer,
                                     String expectedAudience, int clockSkewSeconds) {
            this.idpCertificate = idpCertificate;
            this.expectedIssuer = expectedIssuer;
            this.expectedAudience = expectedAudience;
            this.clockSkewSeconds = clockSkewSeconds;
        }

        public SamlResult processResponse(String samlXml) {
            try {
                Document doc = parseXmlSecurely(samlXml);

                Element responseElement = doc.getDocumentElement();
                if (!"Response".equals(responseElement.getLocalName())
                        || !SAML_PROTOCOL_NS.equals(responseElement.getNamespaceURI())) {
                    return SamlResult.failure("Root element is not a SAML Response");
                }

                String statusCode = extractStatusCode(responseElement);
                if (!"urn:oasis:names:tc:SAML:2.0:status:Success".equals(statusCode)) {
                    return SamlResult.failure("SAML response status is not Success: " + statusCode);
                }

                if (!verifySignature(doc, idpCertificate)) {
                    return SamlResult.failure("XML signature validation failed");
                }

                NodeList assertions = responseElement.getElementsByTagNameNS(SAML_ASSERTION_NS, "Assertion");
                if (assertions.getLength() == 0) {
                    return SamlResult.failure("No Assertion found in SAML response");
                }
                if (assertions.getLength() > 1) {
                    return SamlResult.failure("Multiple assertions found; expected exactly one");
                }

                Element assertion = (Element) assertions.item(0);

                String issuer = extractIssuer(assertion);
                if (!expectedIssuer.equals(issuer)) {
                    return SamlResult.failure("Unexpected Issuer: " + issuer);
                }

                String conditionError = validateConditions(assertion);
                if (conditionError != null) {
                    return SamlResult.failure(conditionError);
                }

                String nameId = extractNameId(assertion);
                if (nameId == null || nameId.isEmpty()) {
                    return SamlResult.failure("NameID not found in assertion");
                }

                String sessionIndex = extractSessionIndex(assertion);
                Map<String, List<String>> attributes = extractAttributes(assertion);

                return SamlResult.success(nameId, sessionIndex, attributes);

            } catch (Exception e) {
                logger.warning("SAML processing error: " + e.getMessage());
                return SamlResult.failure("Processing error: " + e.getMessage());
            }
        }

        private Document parseXmlSecurely(String xml) throws Exception {
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setNamespaceAware(true);

            dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
            dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            dbf.setXIncludeAware(false);
            dbf.setExpandEntityReferences(false);

            DocumentBuilder db = dbf.newDocumentBuilder();
            db.setErrorHandler(null);

            InputSource is = new InputSource(new StringReader(xml));
            return db.parse(is);
        }

        private boolean verifySignature(Document doc, X509Certificate cert) throws Exception {
            NodeList signatureNodes = doc.getElementsByTagNameNS(XMLDSIG_NS, "Signature");
            if (signatureNodes.getLength() == 0) {
                return false;
            }

            Element signatureElement = (Element) signatureNodes.item(0);

            Node signatureParent = signatureElement.getParentNode();
            if (signatureParent == null || !(signatureParent instanceof Element)) {
                return false;
            }
            String parentLocalName = signatureParent.getLocalName();
            String parentNs = signatureParent.getNamespaceURI();
            boolean signedByResponse = "Response".equals(parentLocalName) && SAML_PROTOCOL_NS.equals(parentNs);
            boolean signedByAssertion = "Assertion".equals(parentLocalName) && SAML_ASSERTION_NS.equals(parentNs);
            if (!signedByResponse && !signedByAssertion) {
                return false;
            }

            DOMValidateContext valContext = new DOMValidateContext(cert.getPublicKey(), signatureElement);
            valContext.setIdAttributeNS(
                    (Element) signatureParent, null, "ID");

            NodeList assertions = doc.getElementsByTagNameNS(SAML_ASSERTION_NS, "Assertion");
            for (int i = 0; i < assertions.getLength(); i++) {
                Element assertionEl = (Element) assertions.item(i);
                valContext.setIdAttributeNS(assertionEl, null, "ID");
            }

            XMLSignatureFactory fac = XMLSignatureFactory.getInstance("DOM");
            XMLSignature signature = fac.unmarshalXMLSignature(valContext);

            boolean coreValid = signature.validate(valContext);
            if (!coreValid) {
                return false;
            }

            List<Reference> refs = signature.getSignedInfo().getReferences();
            if (refs.isEmpty()) {
                return false;
            }
            for (Reference ref : refs) {
                if (!ref.validate(valContext)) {
                    return false;
                }
            }

            return true;
        }

        private String extractStatusCode(Element responseElement) {
            NodeList statusList = responseElement.getElementsByTagNameNS(SAML_PROTOCOL_NS, "Status");
            if (statusList.getLength() == 0) return null;
            Element status = (Element) statusList.item(0);
            NodeList codeList = status.getElementsByTagNameNS(SAML_PROTOCOL_NS, "StatusCode");
            if (codeList.getLength() == 0) return null;
            return ((Element) codeList.item(0)).getAttribute("Value");
        }

        private String extractIssuer(Element assertion) {
            NodeList issuerList = assertion.getElementsByTagNameNS(SAML_ASSERTION_NS, "Issuer");
            if (issuerList.getLength() == 0) return null;
            return issuerList.item(0).getTextContent().trim();
        }

        private String validateConditions(Element assertion) {
            NodeList conditionsList = assertion.getElementsByTagNameNS(SAML_ASSERTION_NS, "Conditions");
            if (conditionsList.getLength() == 0) {
                return null;
            }

            Element conditions = (Element) conditionsList.item(0);
            Instant now = Instant.now();

            String notBefore = conditions.getAttribute("NotBefore");
            if (notBefore != null && !notBefore.isEmpty()) {
                try {
                    Instant nbInstant = Instant.parse(notBefore);
                    if (now.plusSeconds(clockSkewSeconds).isBefore(nbInstant)) {
                        return "Assertion is not yet valid (NotBefore: " + notBefore + ")";
                    }
                } catch (DateTimeParseException e) {
                    return "Invalid NotBefore timestamp";
                }
            }

            String notOnOrAfter = conditions.getAttribute("NotOnOrAfter");
            if (notOnOrAfter != null && !notOnOrAfter.isEmpty()) {
                try {
                    Instant noaInstant = Instant.parse(notOnOrAfter);
                    if (now.minusSeconds(clockSkewSeconds).isAfter(noaInstant)
                            || now.minusSeconds(clockSkewSeconds).equals(noaInstant)) {
                        return "Assertion has expired (NotOnOrAfter: " + notOnOrAfter + ")";
                    }
                } catch (DateTimeParseException e) {
                    return "Invalid NotOnOrAfter timestamp";
                }
            }

            NodeList audienceRestrictions = conditions.getElementsByTagNameNS(
                    SAML_ASSERTION_NS, "AudienceRestriction");
            for (int i = 0; i < audienceRestrictions.getLength(); i++) {
                Element restriction = (Element) audienceRestrictions.item(i);
                NodeList audiences = restriction.getElementsByTagNameNS(SAML_ASSERTION_NS, "Audience");
                boolean audienceMatch = false;
                for (int j = 0; j < audiences.getLength(); j++) {
                    String audienceValue = audiences.item(j).getTextContent().trim();
                    if (expectedAudience.equals(audienceValue)) {
                        audienceMatch = true;
                        break;
                    }
                }
                if (!audienceMatch) {
                    return "Audience restriction not satisfied; expected: " + expectedAudience;
                }
            }

            return null;
        }

        private String extractNameId(Element assertion) {
            NodeList subjectList = assertion.getElementsByTagNameNS(SAML_ASSERTION_NS, "Subject");
            if (subjectList.getLength() == 0) return null;
            Element subject = (Element) subjectList.item(0);
            NodeList nameIdList = subject.getElementsByTagNameNS(SAML_ASSERTION_NS, "NameID");
            if (nameIdList.getLength() == 0) return null;
            return nameIdList.item(0).getTextContent().trim();
        }

        private String extractSessionIndex(Element assertion) {
            NodeList authnStatements = assertion.getElementsByTagNameNS(
                    SAML_ASSERTION_NS, "AuthnStatement");
            if (authnStatements.getLength() == 0) return null;
            Element authnStatement = (Element) authnStatements.item(0);
            String idx = authnStatement.getAttribute("SessionIndex");
            return (idx != null && !idx.isEmpty()) ? idx : null;
        }

        private Map<String, List<String>> extractAttributes(Element assertion) {
            Map<String, List<String>> attributes = new LinkedHashMap<>();

            NodeList attrStatements = assertion.getElementsByTagNameNS(
                    SAML_ASSERTION_NS, "AttributeStatement");
            for (int i = 0; i < attrStatements.getLength(); i++) {
                Element attrStatement = (Element) attrStatements.item(i);
                NodeList attrNodes = attrStatement.getElementsByTagNameNS(
                        SAML_ASSERTION_NS, "Attribute");

                for (int j = 0; j < attrNodes.getLength(); j++) {
                    Element attr = (Element) attrNodes.item(j);
                    String name = attr.getAttribute("Name");
                    if (name == null || name.isEmpty()) continue;

                    List<String> values = new ArrayList<>();
                    NodeList valueNodes = attr.getElementsByTagNameNS(
                            SAML_ASSERTION_NS, "AttributeValue");
                    for (int k = 0; k < valueNodes.getLength(); k++) {
                        values.add(valueNodes.item(k).getTextContent().trim());
                    }
                    attributes.put(name, values);
                }
            }

            return attributes;
        }
    }
}
