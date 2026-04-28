import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

import javax.xml.XMLConstants;
import javax.xml.namespace.NamespaceContext;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public final class SamlResponseProcessorApp {

    private static final String SAML_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol";
    private static final String SAML_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion";

    private SamlResponseProcessorApp() {
    }

    public static void main(String[] args) throws Exception {
        String input = readInput(args);
        SamlResponseProcessor processor = new SamlResponseProcessor(new InMemorySessionStore());
        SamlProcessingResult result = processor.process(input);
        System.out.println(result.toJson());
    }

    private static String readInput(String[] args) throws IOException {
        if (args.length > 0) {
            return Files.readString(Path.of(args[0]), StandardCharsets.UTF_8);
        }

        byte[] stdinBytes = System.in.readAllBytes();
        if (stdinBytes.length == 0) {
            throw new IllegalArgumentException("Provide a SAML response XML file path or pipe the XML response to stdin.");
        }
        return new String(stdinBytes, StandardCharsets.UTF_8);
    }

    public static final class SamlResponseProcessor {
        private final SessionStore sessionStore;
        private final SecureRandom secureRandom = new SecureRandom();

        public SamlResponseProcessor(SessionStore sessionStore) {
            this.sessionStore = Objects.requireNonNull(sessionStore, "sessionStore");
        }

        public SamlProcessingResult process(String rawInput) throws Exception {
            String samlXml = normalizeInput(rawInput);
            Document document = parseXml(samlXml);
            ResponseMetadata responseMetadata = validateResponse(document);
            List<AssertionData> assertions = extractAssertions(document);
            if (assertions.isEmpty()) {
                throw new SamlValidationException("SAML Response does not contain any Assertion elements.");
            }

            List<AuthenticatedSession> sessions = new ArrayList<>();
            for (AssertionData assertion : assertions) {
                sessions.add(createAuthenticatedSession(assertion));
            }

            return new SamlProcessingResult(responseMetadata, assertions, sessions);
        }

        private String normalizeInput(String rawInput) {
            String trimmed = Objects.requireNonNull(rawInput, "rawInput").trim();
            if (trimmed.isEmpty()) {
                throw new IllegalArgumentException("SAML response input is empty.");
            }
            if (trimmed.startsWith("<")) {
                return trimmed;
            }

            try {
                byte[] decoded = Base64.getMimeDecoder().decode(trimmed);
                String decodedText = new String(decoded, StandardCharsets.UTF_8).trim();
                if (!decodedText.startsWith("<")) {
                    throw new SamlValidationException("Decoded SAML response is not valid XML.");
                }
                return decodedText;
            } catch (IllegalArgumentException ex) {
                throw new SamlValidationException("Input is neither XML nor Base64-encoded SAML XML.", ex);
            }
        }

        private Document parseXml(String xml) throws Exception {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new InputSource(new java.io.StringReader(xml)));
        }

        private ResponseMetadata validateResponse(Document document) throws Exception {
            Element root = document.getDocumentElement();
            if (root == null) {
                throw new SamlValidationException("XML document does not contain a root element.");
            }
            if (!"Response".equals(root.getLocalName()) || !SAML_PROTOCOL_NS.equals(root.getNamespaceURI())) {
                throw new SamlValidationException("Root element must be samlp:Response in the SAML 2.0 protocol namespace.");
            }

            String responseId = requireAttribute(root, "ID");
            String version = requireAttribute(root, "Version");
            String issueInstantRaw = requireAttribute(root, "IssueInstant");
            if (!"2.0".equals(version)) {
                throw new SamlValidationException("Unsupported SAML version: " + version);
            }

            Instant issueInstant = parseInstant(issueInstantRaw, "Response/@IssueInstant");

            String destination = root.getAttribute("Destination");
            if (!destination.isBlank()) {
                validateUri(destination, "Response/@Destination");
            }

            String issuer = evaluateOptionalString(document, "/samlp:Response/saml:Issuer/text()");
            return new ResponseMetadata(responseId, version, issueInstant, destination.isBlank() ? null : destination, issuer);
        }

        private List<AssertionData> extractAssertions(Document document) throws Exception {
            XPath xpath = newXPath();
            NodeList assertionNodes = (NodeList) xpath.evaluate("/samlp:Response/saml:Assertion", document, XPathConstants.NODESET);
            List<AssertionData> assertions = new ArrayList<>();

            for (int i = 0; i < assertionNodes.getLength(); i++) {
                Element assertionElement = (Element) assertionNodes.item(i);
                String assertionId = requireAttribute(assertionElement, "ID");
                Instant issueInstant = parseInstant(requireAttribute(assertionElement, "IssueInstant"), "Assertion/@IssueInstant");
                String issuer = evaluateOptionalString(assertionElement, "./saml:Issuer/text()");
                String nameId = evaluateOptionalString(assertionElement, "./saml:Subject/saml:NameID/text()");
                if (nameId == null || nameId.isBlank()) {
                    throw new SamlValidationException("Assertion " + assertionId + " is missing Subject/NameID.");
                }

                String notBeforeRaw = evaluateOptionalString(assertionElement, "./saml:Conditions/@NotBefore");
                String notOnOrAfterRaw = evaluateOptionalString(assertionElement, "./saml:Conditions/@NotOnOrAfter");
                String sessionNotOnOrAfterRaw = evaluateOptionalString(assertionElement, "./saml:AuthnStatement/@SessionNotOnOrAfter");
                Node authnStatement = (Node) xpath.evaluate("./saml:AuthnStatement", assertionElement, XPathConstants.NODE);
                if (authnStatement == null) {
                    throw new SamlValidationException("Assertion " + assertionId + " does not contain an AuthnStatement.");
                }

                Instant notBefore = notBeforeRaw == null ? null : parseInstant(notBeforeRaw, "Assertion/Conditions/@NotBefore");
                Instant notOnOrAfter = notOnOrAfterRaw == null ? null : parseInstant(notOnOrAfterRaw, "Assertion/Conditions/@NotOnOrAfter");
                Instant sessionNotOnOrAfter = sessionNotOnOrAfterRaw == null ? null : parseInstant(sessionNotOnOrAfterRaw, "Assertion/AuthnStatement/@SessionNotOnOrAfter");

                Map<String, List<String>> attributes = extractAttributes(xpath, assertionElement);
                assertions.add(new AssertionData(assertionId, issueInstant, issuer, nameId, notBefore, notOnOrAfter, sessionNotOnOrAfter, attributes));
            }

            return assertions;
        }

        private Map<String, List<String>> extractAttributes(XPath xpath, Element assertionElement) throws XPathExpressionException {
            NodeList attributeNodes = (NodeList) xpath.evaluate("./saml:AttributeStatement/saml:Attribute", assertionElement, XPathConstants.NODESET);
            Map<String, List<String>> attributes = new LinkedHashMap<>();
            for (int i = 0; i < attributeNodes.getLength(); i++) {
                Element attribute = (Element) attributeNodes.item(i);
                String name = attribute.getAttribute("Name");
                if (name == null || name.isBlank()) {
                    throw new SamlValidationException("Assertion contains Attribute without a Name.");
                }

                NodeList valueNodes = attribute.getElementsByTagNameNS(SAML_ASSERTION_NS, "AttributeValue");
                List<String> values = new ArrayList<>();
                for (int j = 0; j < valueNodes.getLength(); j++) {
                    String value = valueNodes.item(j).getTextContent();
                    if (value != null) {
                        values.add(value.trim());
                    }
                }
                attributes.put(name, Collections.unmodifiableList(values));
            }
            return Collections.unmodifiableMap(attributes);
        }

        private AuthenticatedSession createAuthenticatedSession(AssertionData assertion) {
            Instant now = Instant.now();
            if (assertion.notBefore != null && now.isBefore(assertion.notBefore)) {
                throw new SamlValidationException("Assertion " + assertion.assertionId + " is not yet valid.");
            }
            if (assertion.notOnOrAfter != null && !now.isBefore(assertion.notOnOrAfter)) {
                throw new SamlValidationException("Assertion " + assertion.assertionId + " has expired.");
            }
            if (assertion.sessionNotOnOrAfter != null && !now.isBefore(assertion.sessionNotOnOrAfter)) {
                throw new SamlValidationException("Assertion " + assertion.assertionId + " session window has expired.");
            }

            Instant expiresAt = earliest(assertion.notOnOrAfter, assertion.sessionNotOnOrAfter)
                    .orElseThrow(() -> new SamlValidationException(
                            "Assertion " + assertion.assertionId + " does not contain a usable session expiration."));

            String sessionId = generateSessionId();
            AuthenticatedSession session = new AuthenticatedSession(
                    sessionId,
                    assertion.nameId,
                    assertion.assertionId,
                    now,
                    expiresAt,
                    assertion.attributes
            );
            sessionStore.save(session);
            return session;
        }

        private Optional<Instant> earliest(Instant first, Instant second) {
            if (first == null && second == null) {
                return Optional.empty();
            }
            if (first == null) {
                return Optional.of(second);
            }
            if (second == null) {
                return Optional.of(first);
            }
            return Optional.of(first.isBefore(second) ? first : second);
        }

        private String generateSessionId() {
            byte[] randomBytes = new byte[32];
            secureRandom.nextBytes(randomBytes);
            return Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
        }

        private XPath newXPath() {
            XPath xpath = XPathFactory.newInstance().newXPath();
            xpath.setNamespaceContext(new SamlNamespaceContext());
            return xpath;
        }

        private String requireAttribute(Element element, String attributeName) {
            String value = element.getAttribute(attributeName);
            if (value == null || value.isBlank()) {
                throw new SamlValidationException(
                        "Element " + element.getLocalName() + " is missing required attribute " + attributeName + ".");
            }
            return value;
        }

        private String evaluateOptionalString(Object context, String expression) throws XPathExpressionException {
            String value = newXPath().evaluate(expression, context);
            if (value == null) {
                return null;
            }
            String trimmed = value.trim();
            return trimmed.isEmpty() ? null : trimmed;
        }

        private Instant parseInstant(String value, String fieldName) {
            try {
                return Instant.parse(value);
            } catch (DateTimeParseException ex) {
                throw new SamlValidationException("Invalid timestamp for " + fieldName + ": " + value, ex);
            }
        }

        private void validateUri(String value, String fieldName) {
            try {
                new URI(value);
            } catch (URISyntaxException ex) {
                throw new SamlValidationException("Invalid URI for " + fieldName + ": " + value, ex);
            }
        }
    }

    public interface SessionStore {
        void save(AuthenticatedSession session);

        AuthenticatedSession findById(String sessionId);
    }

    public static final class InMemorySessionStore implements SessionStore {
        private final Map<String, AuthenticatedSession> sessions = new ConcurrentHashMap<>();

        @Override
        public void save(AuthenticatedSession session) {
            sessions.put(session.sessionId, session);
        }

        @Override
        public AuthenticatedSession findById(String sessionId) {
            return sessions.get(sessionId);
        }
    }

    public static final class AuthenticatedSession {
        private final String sessionId;
        private final String principal;
        private final String assertionId;
        private final Instant authenticatedAt;
        private final Instant expiresAt;
        private final Map<String, List<String>> attributes;

        public AuthenticatedSession(
                String sessionId,
                String principal,
                String assertionId,
                Instant authenticatedAt,
                Instant expiresAt,
                Map<String, List<String>> attributes
        ) {
            this.sessionId = sessionId;
            this.principal = principal;
            this.assertionId = assertionId;
            this.authenticatedAt = authenticatedAt;
            this.expiresAt = expiresAt;
            this.attributes = attributes;
        }

        public String toJson() {
            return "{"
                    + "\"sessionId\":\"" + jsonEscape(sessionId) + "\","
                    + "\"principal\":\"" + jsonEscape(principal) + "\","
                    + "\"assertionId\":\"" + jsonEscape(assertionId) + "\","
                    + "\"authenticatedAt\":\"" + authenticatedAt + "\","
                    + "\"expiresAt\":\"" + expiresAt + "\","
                    + "\"attributes\":" + attributesToJson(attributes)
                    + "}";
        }
    }

    public static final class AssertionData {
        private final String assertionId;
        private final Instant issueInstant;
        private final String issuer;
        private final String nameId;
        private final Instant notBefore;
        private final Instant notOnOrAfter;
        private final Instant sessionNotOnOrAfter;
        private final Map<String, List<String>> attributes;

        public AssertionData(
                String assertionId,
                Instant issueInstant,
                String issuer,
                String nameId,
                Instant notBefore,
                Instant notOnOrAfter,
                Instant sessionNotOnOrAfter,
                Map<String, List<String>> attributes
        ) {
            this.assertionId = assertionId;
            this.issueInstant = issueInstant;
            this.issuer = issuer;
            this.nameId = nameId;
            this.notBefore = notBefore;
            this.notOnOrAfter = notOnOrAfter;
            this.sessionNotOnOrAfter = sessionNotOnOrAfter;
            this.attributes = attributes;
        }

        public String toJson() {
            return "{"
                    + "\"assertionId\":\"" + jsonEscape(assertionId) + "\","
                    + "\"issueInstant\":\"" + issueInstant + "\","
                    + "\"issuer\":" + toJsonStringOrNull(issuer) + ","
                    + "\"nameId\":\"" + jsonEscape(nameId) + "\","
                    + "\"notBefore\":" + toJsonInstantOrNull(notBefore) + ","
                    + "\"notOnOrAfter\":" + toJsonInstantOrNull(notOnOrAfter) + ","
                    + "\"sessionNotOnOrAfter\":" + toJsonInstantOrNull(sessionNotOnOrAfter) + ","
                    + "\"attributes\":" + attributesToJson(attributes)
                    + "}";
        }
    }

    public static final class ResponseMetadata {
        private final String responseId;
        private final String version;
        private final Instant issueInstant;
        private final String destination;
        private final String issuer;

        public ResponseMetadata(String responseId, String version, Instant issueInstant, String destination, String issuer) {
            this.responseId = responseId;
            this.version = version;
            this.issueInstant = issueInstant;
            this.destination = destination;
            this.issuer = issuer;
        }

        public String toJson() {
            return "{"
                    + "\"responseId\":\"" + jsonEscape(responseId) + "\","
                    + "\"version\":\"" + jsonEscape(version) + "\","
                    + "\"issueInstant\":\"" + issueInstant + "\","
                    + "\"destination\":" + toJsonStringOrNull(destination) + ","
                    + "\"issuer\":" + toJsonStringOrNull(issuer)
                    + "}";
        }
    }

    public static final class SamlProcessingResult {
        private final ResponseMetadata response;
        private final List<AssertionData> assertions;
        private final List<AuthenticatedSession> sessions;

        public SamlProcessingResult(ResponseMetadata response, List<AssertionData> assertions, List<AuthenticatedSession> sessions) {
            this.response = response;
            this.assertions = List.copyOf(assertions);
            this.sessions = List.copyOf(sessions);
        }

        public String toJson() {
            StringBuilder builder = new StringBuilder();
            builder.append("{");
            builder.append("\"response\":").append(response.toJson()).append(",");
            builder.append("\"assertions\":[");
            for (int i = 0; i < assertions.size(); i++) {
                if (i > 0) {
                    builder.append(",");
                }
                builder.append(assertions.get(i).toJson());
            }
            builder.append("],");
            builder.append("\"sessions\":[");
            for (int i = 0; i < sessions.size(); i++) {
                if (i > 0) {
                    builder.append(",");
                }
                builder.append(sessions.get(i).toJson());
            }
            builder.append("]");
            builder.append("}");
            return builder.toString();
        }
    }

    public static final class SamlValidationException extends RuntimeException {
        public SamlValidationException(String message) {
            super(message);
        }

        public SamlValidationException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    public static final class SamlNamespaceContext implements NamespaceContext {
        private static final Map<String, String> PREFIXES;

        static {
            Map<String, String> prefixes = new HashMap<>();
            prefixes.put("samlp", SAML_PROTOCOL_NS);
            prefixes.put("saml", SAML_ASSERTION_NS);
            PREFIXES = Collections.unmodifiableMap(prefixes);
        }

        @Override
        public String getNamespaceURI(String prefix) {
            return PREFIXES.getOrDefault(prefix, XMLConstants.NULL_NS_URI);
        }

        @Override
        public String getPrefix(String namespaceURI) {
            for (Map.Entry<String, String> entry : PREFIXES.entrySet()) {
                if (entry.getValue().equals(namespaceURI)) {
                    return entry.getKey();
                }
            }
            return null;
        }

        @Override
        public java.util.Iterator<String> getPrefixes(String namespaceURI) {
            String prefix = getPrefix(namespaceURI);
            return prefix == null ? Collections.emptyIterator() : Collections.singleton(prefix).iterator();
        }
    }

    private static String attributesToJson(Map<String, List<String>> attributes) {
        StringBuilder builder = new StringBuilder();
        builder.append("{");
        int i = 0;
        for (Map.Entry<String, List<String>> entry : attributes.entrySet()) {
            if (i++ > 0) {
                builder.append(",");
            }
            builder.append("\"").append(jsonEscape(entry.getKey())).append("\":[");
            for (int j = 0; j < entry.getValue().size(); j++) {
                if (j > 0) {
                    builder.append(",");
                }
                builder.append("\"").append(jsonEscape(entry.getValue().get(j))).append("\"");
            }
            builder.append("]");
        }
        builder.append("}");
        return builder.toString();
    }

    private static String toJsonStringOrNull(String value) {
        return value == null ? "null" : "\"" + jsonEscape(value) + "\"";
    }

    private static String toJsonInstantOrNull(Instant value) {
        return value == null ? "null" : "\"" + value + "\"";
    }

    private static String jsonEscape(String value) {
        StringBuilder escaped = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '"' -> escaped.append("\\\"");
                case '\\' -> escaped.append("\\\\");
                case '\b' -> escaped.append("\\b");
                case '\f' -> escaped.append("\\f");
                case '\n' -> escaped.append("\\n");
                case '\r' -> escaped.append("\\r");
                case '\t' -> escaped.append("\\t");
                default -> {
                    if (ch < 0x20) {
                        escaped.append(String.format("\\u%04x", (int) ch));
                    } else {
                        escaped.append(ch);
                    }
                }
            }
        }
        return escaped.toString();
    }
}