import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.*;
import org.xml.sax.InputSource;
import java.io.StringReader;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SamlResponseProcessor {

    private static final String SAML2_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol";
    private static final String SAML2_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion";
    private static final String STATUS_SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success";

    private final ConcurrentHashMap<String, AuthenticatedSession> activeSessions = new ConcurrentHashMap<>();
    private final Set<String> processedResponseIds = Collections.synchronizedSet(new LinkedHashSet<>() {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Boolean> eldest) {
            return size() > 10000;
        }

        // LinkedHashSet doesn't have removeEldestEntry, so we use a LinkedHashMap wrapper
    });
    private final Map<String, Boolean> processedResponseIdMap = Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, false) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Boolean> eldest) {
            return size() > 10000;
        }
    });

    public static void main(String[] args) {
        SamlResponseProcessor processor = new SamlResponseProcessor();

        String sampleSamlResponse = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            + "<samlp:Response xmlns:samlp=\"urn:oasis:names:tc:SAML:2.0:protocol\" "
            + "xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\" "
            + "ID=\"_response_123\" Version=\"2.0\" "
            + "IssueInstant=\"2026-03-31T12:00:00Z\" "
            + "Destination=\"https://sp.example.com/acs\">"
            + "<samlp:Status><samlp:StatusCode Value=\"urn:oasis:names:tc:SAML:2.0:status:Success\"/></samlp:Status>"
            + "<saml:Assertion ID=\"_assertion_456\" Version=\"2.0\" "
            + "IssueInstant=\"2026-03-31T12:00:00Z\">"
            + "<saml:Issuer>https://idp.example.com</saml:Issuer>"
            + "<saml:Subject>"
            + "<saml:NameID Format=\"urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress\">user@example.com</saml:NameID>"
            + "<saml:SubjectConfirmation Method=\"urn:oasis:names:tc:SAML:2.0:cm:bearer\">"
            + "<saml:SubjectConfirmationData NotOnOrAfter=\"2026-03-31T12:10:00Z\" "
            + "Recipient=\"https://sp.example.com/acs\"/>"
            + "</saml:SubjectConfirmation>"
            + "</saml:Subject>"
            + "<saml:Conditions NotBefore=\"2026-03-31T11:55:00Z\" NotOnOrAfter=\"2026-03-31T12:10:00Z\">"
            + "<saml:AudienceRestriction><saml:Audience>https://sp.example.com</saml:Audience></saml:AudienceRestriction>"
            + "</saml:Conditions>"
            + "<saml:AuthnStatement AuthnInstant=\"2026-03-31T12:00:00Z\" SessionIndex=\"_session_789\">"
            + "<saml:AuthnContext><saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef></saml:AuthnContext>"
            + "</saml:AuthnStatement>"
            + "<saml:AttributeStatement>"
            + "<saml:Attribute Name=\"firstName\"><saml:AttributeValue>Jane</saml:AttributeValue></saml:Attribute>"
            + "<saml:Attribute Name=\"lastName\"><saml:AttributeValue>Doe</saml:AttributeValue></saml:Attribute>"
            + "<saml:Attribute Name=\"role\"><saml:AttributeValue>admin</saml:AttributeValue></saml:Attribute>"
            + "<saml:Attribute Name=\"department\"><saml:AttributeValue>Engineering</saml:AttributeValue></saml:Attribute>"
            + "</saml:AttributeStatement>"
            + "</saml:Assertion>"
            + "</samlp:Response>";

        try {
            AuthenticatedSession session = processor.processSamlResponse(sampleSamlResponse);
            System.out.println("Session created successfully:");
            System.out.println("  Session ID: " + session.getSessionId());
            System.out.println("  Subject: " + session.getSubject());
            System.out.println("  Issuer: " + session.getIssuer());
            System.out.println("  Attributes:");
            session.getAttributes().forEach((k, v) ->
                System.out.println("    " + k + " = " + String.join(", ", v)));
            System.out.println("  Expires: " + session.getExpiresAt());
        } catch (SamlProcessingException e) {
            System.err.println("SAML processing failed: " + e.getMessage());
        }
    }

    public AuthenticatedSession processSamlResponse(String samlXml) throws SamlProcessingException {
        if (samlXml == null || samlXml.isBlank()) {
            throw new SamlProcessingException("SAML response is null or empty");
        }

        Document document = parseXml(samlXml);
        Element responseElement = validateResponseElement(document);
        validateStatus(responseElement);
        SamlAssertion assertion = extractAssertion(responseElement);
        validateAssertion(assertion);
        return createSession(assertion);
    }

    private Document parseXml(String xml) throws SamlProcessingException {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);

            // Prevent XXE attacks
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);

            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new InputSource(new StringReader(xml)));
        } catch (Exception e) {
            throw new SamlProcessingException("Failed to parse SAML XML: " + e.getMessage());
        }
    }

    private Element validateResponseElement(Document document) throws SamlProcessingException {
        NodeList responseNodes = document.getElementsByTagNameNS(SAML2_PROTOCOL_NS, "Response");
        if (responseNodes.getLength() == 0) {
            throw new SamlProcessingException("No SAML Response element found");
        }
        if (responseNodes.getLength() > 1) {
            throw new SamlProcessingException("Multiple Response elements found");
        }

        Element response = (Element) responseNodes.item(0);

        String version = response.getAttribute("Version");
        if (!"2.0".equals(version)) {
            throw new SamlProcessingException("Unsupported SAML version: " + version);
        }

        String responseId = response.getAttribute("ID");
        if (responseId == null || responseId.isBlank()) {
            throw new SamlProcessingException("Response missing required ID attribute");
        }

        if (processedResponseIdMap.putIfAbsent(responseId, Boolean.TRUE) != null) {
            throw new SamlProcessingException("Replay detected: Response ID already processed");
        }

        String issueInstant = response.getAttribute("IssueInstant");
        if (issueInstant == null || issueInstant.isBlank()) {
            throw new SamlProcessingException("Response missing required IssueInstant attribute");
        }

        try {
            Instant issued = Instant.parse(issueInstant);
            Instant now = Instant.now();
            if (issued.isAfter(now.plusSeconds(300))) {
                throw new SamlProcessingException("Response IssueInstant is in the future");
            }
            if (issued.isBefore(now.minusSeconds(600))) {
                throw new SamlProcessingException("Response IssueInstant is too old");
            }
        } catch (DateTimeParseException e) {
            throw new SamlProcessingException("Invalid IssueInstant format: " + issueInstant);
        }

        return response;
    }

    private void validateStatus(Element response) throws SamlProcessingException {
        NodeList statusNodes = response.getElementsByTagNameNS(SAML2_PROTOCOL_NS, "Status");
        if (statusNodes.getLength() == 0) {
            throw new SamlProcessingException("Response missing Status element");
        }

        Element status = (Element) statusNodes.item(0);
        NodeList statusCodeNodes = status.getElementsByTagNameNS(SAML2_PROTOCOL_NS, "StatusCode");
        if (statusCodeNodes.getLength() == 0) {
            throw new SamlProcessingException("Status missing StatusCode element");
        }

        Element statusCode = (Element) statusCodeNodes.item(0);
        String value = statusCode.getAttribute("Value");
        if (!STATUS_SUCCESS.equals(value)) {
            throw new SamlProcessingException("SAML authentication failed with status: " + value);
        }
    }

    private SamlAssertion extractAssertion(Element response) throws SamlProcessingException {
        NodeList assertionNodes = response.getElementsByTagNameNS(SAML2_ASSERTION_NS, "Assertion");
        if (assertionNodes.getLength() == 0) {
            throw new SamlProcessingException("No Assertion element found in Response");
        }

        Element assertionElement = (Element) assertionNodes.item(0);

        String assertionId = assertionElement.getAttribute("ID");
        if (assertionId == null || assertionId.isBlank()) {
            throw new SamlProcessingException("Assertion missing required ID attribute");
        }

        SamlAssertion assertion = new SamlAssertion();
        assertion.setId(assertionId);

        // Extract Issuer
        NodeList issuerNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "Issuer");
        if (issuerNodes.getLength() > 0) {
            assertion.setIssuer(issuerNodes.item(0).getTextContent().trim());
        }

        // Extract Subject/NameID
        NodeList nameIdNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "NameID");
        if (nameIdNodes.getLength() > 0) {
            Element nameId = (Element) nameIdNodes.item(0);
            assertion.setSubject(nameId.getTextContent().trim());
            assertion.setNameIdFormat(nameId.getAttribute("Format"));
        }

        // Extract Conditions
        NodeList conditionsNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "Conditions");
        if (conditionsNodes.getLength() > 0) {
            Element conditions = (Element) conditionsNodes.item(0);
            String notBefore = conditions.getAttribute("NotBefore");
            String notOnOrAfter = conditions.getAttribute("NotOnOrAfter");
            if (!notBefore.isBlank()) {
                assertion.setNotBefore(Instant.parse(notBefore));
            }
            if (!notOnOrAfter.isBlank()) {
                assertion.setNotOnOrAfter(Instant.parse(notOnOrAfter));
            }

            // Extract Audience
            NodeList audienceNodes = conditions.getElementsByTagNameNS(SAML2_ASSERTION_NS, "Audience");
            for (int i = 0; i < audienceNodes.getLength(); i++) {
                assertion.getAudiences().add(audienceNodes.item(i).getTextContent().trim());
            }
        }

        // Extract SubjectConfirmationData
        NodeList subConfDataNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "SubjectConfirmationData");
        if (subConfDataNodes.getLength() > 0) {
            Element subConfData = (Element) subConfDataNodes.item(0);
            String notOnOrAfter = subConfData.getAttribute("NotOnOrAfter");
            if (!notOnOrAfter.isBlank()) {
                assertion.setSubjectNotOnOrAfter(Instant.parse(notOnOrAfter));
            }
        }

        // Extract AuthnStatement
        NodeList authnNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "AuthnStatement");
        if (authnNodes.getLength() > 0) {
            Element authnStatement = (Element) authnNodes.item(0);
            assertion.setSessionIndex(authnStatement.getAttribute("SessionIndex"));

            NodeList authnContextRef = authnStatement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "AuthnContextClassRef");
            if (authnContextRef.getLength() > 0) {
                assertion.setAuthnContextClassRef(authnContextRef.item(0).getTextContent().trim());
            }
        }

        // Extract Attributes
        NodeList attributeNodes = assertionElement.getElementsByTagNameNS(SAML2_ASSERTION_NS, "Attribute");
        for (int i = 0; i < attributeNodes.getLength(); i++) {
            Element attr = (Element) attributeNodes.item(i);
            String name = attr.getAttribute("Name");
            if (name.isBlank()) continue;

            List<String> values = new ArrayList<>();
            NodeList valueNodes = attr.getElementsByTagNameNS(SAML2_ASSERTION_NS, "AttributeValue");
            for (int j = 0; j < valueNodes.getLength(); j++) {
                values.add(valueNodes.item(j).getTextContent().trim());
            }
            assertion.getAttributes().put(name, values);
        }

        return assertion;
    }

    private void validateAssertion(SamlAssertion assertion) throws SamlProcessingException {
        if (assertion.getSubject() == null || assertion.getSubject().isBlank()) {
            throw new SamlProcessingException("Assertion missing Subject/NameID");
        }

        if (assertion.getIssuer() == null || assertion.getIssuer().isBlank()) {
            throw new SamlProcessingException("Assertion missing Issuer");
        }

        Instant now = Instant.now();

        if (assertion.getNotBefore() != null && now.isBefore(assertion.getNotBefore())) {
            throw new SamlProcessingException("Assertion is not yet valid (NotBefore condition)");
        }

        if (assertion.getNotOnOrAfter() != null && !now.isBefore(assertion.getNotOnOrAfter())) {
            throw new SamlProcessingException("Assertion has expired (NotOnOrAfter condition)");
        }

        if (assertion.getSubjectNotOnOrAfter() != null && !now.isBefore(assertion.getSubjectNotOnOrAfter())) {
            throw new SamlProcessingException("Subject confirmation has expired");
        }
    }

    private AuthenticatedSession createSession(SamlAssertion assertion) {
        String sessionId = UUID.randomUUID().toString();
        Instant expiresAt = assertion.getNotOnOrAfter() != null
            ? assertion.getNotOnOrAfter()
            : Instant.now().plusSeconds(3600);

        AuthenticatedSession session = new AuthenticatedSession(
            sessionId,
            assertion.getSubject(),
            assertion.getIssuer(),
            assertion.getNameIdFormat(),
            assertion.getAttributes(),
            assertion.getSessionIndex(),
            assertion.getAuthnContextClassRef(),
            Instant.now(),
            expiresAt
        );

        activeSessions.put(sessionId, session);
        return session;
    }

    public Optional<AuthenticatedSession> getSession(String sessionId) {
        AuthenticatedSession session = activeSessions.get(sessionId);
        if (session == null) {
            return Optional.empty();
        }
        if (!Instant.now().isBefore(session.getExpiresAt())) {
            activeSessions.remove(sessionId);
            return Optional.empty();
        }
        return Optional.of(session);
    }

    public void invalidateSession(String sessionId) {
        activeSessions.remove(sessionId);
    }

    // --- Inner classes ---

    static class SamlAssertion {
        private String id;
        private String issuer;
        private String subject;
        private String nameIdFormat;
        private Instant notBefore;
        private Instant notOnOrAfter;
        private Instant subjectNotOnOrAfter;
        private String sessionIndex;
        private String authnContextClassRef;
        private final List<String> audiences = new ArrayList<>();
        private final Map<String, List<String>> attributes = new LinkedHashMap<>();

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getIssuer() { return issuer; }
        public void setIssuer(String issuer) { this.issuer = issuer; }
        public String getSubject() { return subject; }
        public void setSubject(String subject) { this.subject = subject; }
        public String getNameIdFormat() { return nameIdFormat; }
        public void setNameIdFormat(String nameIdFormat) { this.nameIdFormat = nameIdFormat; }
        public Instant getNotBefore() { return notBefore; }
        public void setNotBefore(Instant notBefore) { this.notBefore = notBefore; }
        public Instant getNotOnOrAfter() { return notOnOrAfter; }
        public void setNotOnOrAfter(Instant notOnOrAfter) { this.notOnOrAfter = notOnOrAfter; }
        public Instant getSubjectNotOnOrAfter() { return subjectNotOnOrAfter; }
        public void setSubjectNotOnOrAfter(Instant subjectNotOnOrAfter) { this.subjectNotOnOrAfter = subjectNotOnOrAfter; }
        public String getSessionIndex() { return sessionIndex; }
        public void setSessionIndex(String sessionIndex) { this.sessionIndex = sessionIndex; }
        public String getAuthnContextClassRef() { return authnContextClassRef; }
        public void setAuthnContextClassRef(String authnContextClassRef) { this.authnContextClassRef = authnContextClassRef; }
        public List<String> getAudiences() { return audiences; }
        public Map<String, List<String>> getAttributes() { return attributes; }
    }

    static class AuthenticatedSession {
        private final String sessionId;
        private final String subject;
        private final String issuer;
        private final String nameIdFormat;
        private final Map<String, List<String>> attributes;
        private final String sessionIndex;
        private final String authnContextClassRef;
        private final Instant createdAt;
        private final Instant expiresAt;

        public AuthenticatedSession(String sessionId, String subject, String issuer,
                String nameIdFormat, Map<String, List<String>> attributes,
                String sessionIndex, String authnContextClassRef,
                Instant createdAt, Instant expiresAt) {
            this.sessionId = sessionId;
            this.subject = subject;
            this.issuer = issuer;
            this.nameIdFormat = nameIdFormat;
            this.attributes = Collections.unmodifiableMap(new LinkedHashMap<>(attributes));
            this.sessionIndex = sessionIndex;
            this.authnContextClassRef = authnContextClassRef;
            this.createdAt = createdAt;
            this.expiresAt = expiresAt;
        }

        public String getSessionId() { return sessionId; }
        public String getSubject() { return subject; }
        public String getIssuer() { return issuer; }
        public String getNameIdFormat() { return nameIdFormat; }
        public Map<String, List<String>> getAttributes() { return attributes; }
        public String getSessionIndex() { return sessionIndex; }
        public String getAuthnContextClassRef() { return authnContextClassRef; }
        public Instant getCreatedAt() { return createdAt; }
        public Instant getExpiresAt() { return expiresAt; }
    }

    static class SamlProcessingException extends Exception {
        public SamlProcessingException(String message) {
            super(message);
        }
    }
}