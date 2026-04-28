package com.example.samlsp;

import com.example.samlsp.config.AppSamlProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(AppSamlProperties.class)
public class SamlSpApplication {

    public static void main(String[] args) {
        SpringApplication.run(SamlSpApplication.class, args);
    }
}

src/main/java/com/example/samlsp/config/AppSamlProperties.java
package com.example.samlsp.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.saml")
public class AppSamlProperties {

    private String spEntityId = "urn:example:sp";
    private String acsUrl = "http://localhost:8080/saml/acs";
    private String audience = "urn:example:sp";
    private String idpIssuer = "";
    private String sessionAttributeName = "samlAttributes";
    private String trustedCertificate = "";

    public String getSpEntityId() {
        return spEntityId;
    }

    public void setSpEntityId(String spEntityId) {
        this.spEntityId = spEntityId;
    }

    public String getAcsUrl() {
        return acsUrl;
    }

    public void setAcsUrl(String acsUrl) {
        this.acsUrl = acsUrl;
    }

    public String getAudience() {
        return audience;
    }

    public void setAudience(String audience) {
        this.audience = audience;
    }

    public String getIdpIssuer() {
        return idpIssuer;
    }

    public void setIdpIssuer(String idpIssuer) {
        this.idpIssuer = idpIssuer;
    }

    public String getSessionAttributeName() {
        return sessionAttributeName;
    }

    public void setSessionAttributeName(String sessionAttributeName) {
        this.sessionAttributeName = sessionAttributeName;
    }

    public String getTrustedCertificate() {
        return trustedCertificate;
    }

    public void setTrustedCertificate(String trustedCertificate) {
        this.trustedCertificate = trustedCertificate;
    }
}

src/main/java/com/example/samlsp/config/SecurityConfig.java
package com.example.samlsp.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.ignoringRequestMatchers("/saml/acs"))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/saml/acs", "/error").permitAll()
                .anyRequest().authenticated())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
            .formLogin(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable)
            .logout(Customizer.withDefaults());

        return http.build();
    }
}

src/main/java/com/example/samlsp/controller/HomeController.java
package com.example.samlsp.controller;

import com.example.samlsp.model.SamlSessionPrincipal;
import jakarta.servlet.http.HttpSession;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HomeController {

    @GetMapping("/")
    public Map<String, Object> home(Authentication authentication, HttpSession session) {
        SamlSessionPrincipal principal = (SamlSessionPrincipal) authentication.getPrincipal();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("authenticated", true);
        response.put("nameId", principal.getName());
        response.put("attributes", principal.getAttributes());
        response.put("sessionId", session.getId());
        return response;
    }
}

src/main/java/com/example/samlsp/controller/SamlAcsController.java
package com.example.samlsp.controller;

import com.example.samlsp.service.SamlService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SamlAcsController {

    private final SamlService samlService;

    public SamlAcsController(SamlService samlService) {
        this.samlService = samlService;
    }

    @PostMapping(path = "/saml/acs", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public ResponseEntity<Void> consumeAssertion(
        @RequestParam("SAMLResponse") String samlResponse,
        @RequestParam(value = "RelayState", required = false) String relayState,
        HttpServletRequest request
    ) {
        samlService.authenticate(samlResponse, request);
        String location = (relayState == null || relayState.isBlank()) ? "/" : relayState;
        return ResponseEntity.status(302).header(HttpHeaders.LOCATION, location).build();
    }
}

src/main/java/com/example/samlsp/controller/SamlErrorHandler.java
package com.example.samlsp.controller;

import com.example.samlsp.service.SamlAuthenticationException;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class SamlErrorHandler {

    @ExceptionHandler(SamlAuthenticationException.class)
    public ResponseEntity<Map<String, String>> handleSamlAuthenticationException(SamlAuthenticationException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", ex.getMessage()));
    }
}

src/main/java/com/example/samlsp/model/SamlSessionPrincipal.java
package com.example.samlsp.model;

import java.io.Serial;
import java.io.Serializable;
import java.util.List;
import java.util.Map;

public final class SamlSessionPrincipal implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    private final String name;
    private final Map<String, List<String>> attributes;

    public SamlSessionPrincipal(String name, Map<String, List<String>> attributes) {
        this.name = name;
        this.attributes = attributes;
    }

    public String getName() {
        return name;
    }

    public Map<String, List<String>> getAttributes() {
        return attributes;
    }
}

src/main/java/com/example/samlsp/service/SamlAuthenticationException.java
package com.example.samlsp.service;

public class SamlAuthenticationException extends RuntimeException {

    public SamlAuthenticationException(String message) {
        super(message);
    }

    public SamlAuthenticationException(String message, Throwable cause) {
        super(message, cause);
    }
}

src/main/java/com/example/samlsp/service/SamlService.java
package com.example.samlsp.service;

import com.example.samlsp.config.AppSamlProperties;
import com.example.samlsp.model.SamlSessionPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import javax.xml.XMLConstants;
import javax.xml.crypto.dsig.XMLSignature;
import javax.xml.crypto.dsig.XMLSignatureFactory;
import javax.xml.crypto.dsig.dom.DOMValidateContext;
import javax.xml.namespace.NamespaceContext;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.stereotype.Service;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

@Service
public class SamlService {

    private static final String SAML_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol";
    private static final String SAML_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion";
    private static final String SAML_STATUS_SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success";
    private static final String SUBJECT_CONFIRMATION_BEARER = "urn:oasis:names:tc:SAML:2.0:cm:bearer";
    private static final Duration CLOCK_SKEW = Duration.ofMinutes(2);
    private static final Duration DEFAULT_REPLAY_WINDOW = Duration.ofMinutes(5);

    private final AppSamlProperties properties;
    private final ConcurrentMap<String, Instant> processedIds = new ConcurrentHashMap<>();

    private volatile X509Certificate trustedCertificate;

    public SamlService(AppSamlProperties properties) {
        this.properties = properties;
    }

    public void authenticate(String encodedSamlResponse, HttpServletRequest request) {
        ParsedSamlResponse response = parseResponse(encodedSamlResponse);
        validateResponse(response, request);
        validateAssertion(response, request);

        registerReplay(response.responseId(), resolveReplayExpiry(response));
        registerReplay(response.assertionId(), resolveReplayExpiry(response));

        Map<String, List<String>> attributes = extractAttributes(response.assertionElement());
        String nameId = extractNameId(response.assertionElement());
        Collection<? extends GrantedAuthority> authorities = extractAuthorities(attributes);

        SamlSessionPrincipal principal = new SamlSessionPrincipal(nameId, attributes);
        Authentication authentication =
            new UsernamePasswordAuthenticationToken(principal, "N/A", authorities);

        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(authentication);
        SecurityContextHolder.setContext(context);

        HttpSession session = request.getSession(false);
        if (session != null) {
            request.changeSessionId();
            session = request.getSession(false);
        } else {
            session = request.getSession(true);
        }
        session.setAttribute(properties.getSessionAttributeName(), attributes);
        session.setAttribute("samlNameId", nameId);
        session.setAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY, context);
    }

    private ParsedSamlResponse parseResponse(String encodedSamlResponse) {
        try {
            byte[] xmlBytes = Base64.getDecoder().decode(encodedSamlResponse);
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

            DocumentBuilder builder = factory.newDocumentBuilder();
            Document document = builder.parse(new ByteArrayInputStream(xmlBytes));
            Element root = document.getDocumentElement();
            if (!"Response".equals(root.getLocalName()) || !SAML_PROTOCOL_NS.equals(root.getNamespaceURI())) {
                throw new SamlAuthenticationException("The SAML payload is not a SAML 2.0 response");
            }

            markIdAttributes(root);

            NodeList encryptedAssertions = evaluateNodes(root, "./saml:EncryptedAssertion");
            if (encryptedAssertions.getLength() > 0) {
                throw new SamlAuthenticationException("Encrypted assertions are not supported by this service");
            }

            NodeList assertions = evaluateNodes(root, "./saml:Assertion");
            if (assertions.getLength() != 1) {
                throw new SamlAuthenticationException("Exactly one assertion is required");
            }

            Element assertion = (Element) assertions.item(0);
            String responseId = requireAttribute(root, "ID", "SAML response is missing an ID");
            String assertionId = requireAttribute(assertion, "ID", "Assertion is missing an ID");

            return new ParsedSamlResponse(root, assertion, responseId, assertionId);
        } catch (SamlAuthenticationException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new SamlAuthenticationException("Failed to parse SAML response", ex);
        }
    }

    private void validateResponse(ParsedSamlResponse response, HttpServletRequest request) {
        if (!SAML_STATUS_SUCCESS.equals(evaluateString(
            response.responseElement(),
            "string(./samlp:Status/samlp:StatusCode/@Value)"))) {
            throw new SamlAuthenticationException("SAML response status is not success");
        }
        validateIssuer(evaluateString(response.responseElement(), "string(./saml:Issuer)"));
        validateDestination(response.responseElement().getAttribute("Destination"), request);
        validateReplay(response.responseId());

        boolean responseSigned = hasDirectSignature(response.responseElement());
        boolean assertionSigned = hasDirectSignature(response.assertionElement());
        if (!responseSigned && !assertionSigned) {
            throw new SamlAuthenticationException("Unsigned SAML responses are not accepted");
        }
        if (responseSigned) {
            validateSignature(response.responseElement());
        }
        if (assertionSigned) {
            validateSignature(response.assertionElement());
        }
    }

    private void validateAssertion(ParsedSamlResponse response, HttpServletRequest request) {
        validateReplay(response.assertionId());
        validateIssuer(evaluateString(response.assertionElement(), "string(./saml:Issuer)"));
        validateConditions(response.assertionElement());
        validateSubject(response.assertionElement(), request);
    }

    private void validateConditions(Element assertion) {
        Element conditions = evaluateElement(assertion, "./saml:Conditions");
        if (conditions == null) {
            throw new SamlAuthenticationException("Assertion is missing conditions");
        }

        Instant now = Instant.now();
        Instant notBefore = parseOptionalInstant(conditions.getAttribute("NotBefore"));
        if (notBefore != null && now.isBefore(notBefore.minus(CLOCK_SKEW))) {
            throw new SamlAuthenticationException("Assertion is not yet valid");
        }
        Instant notOnOrAfter = parseOptionalInstant(conditions.getAttribute("NotOnOrAfter"));
        if (notOnOrAfter != null && !now.isBefore(notOnOrAfter.plus(CLOCK_SKEW))) {
            throw new SamlAuthenticationException("Assertion has expired");
        }

        String expectedAudience = isBlank(properties.getAudience())
            ? properties.getSpEntityId()
            : properties.getAudience();
        boolean audienceMatched = false;
        NodeList audiences = evaluateNodes(conditions, "./saml:AudienceRestriction/saml:Audience");
        for (int i = 0; i < audiences.getLength(); i++) {
            String audience = audiences.item(i).getTextContent();
            if (expectedAudience.equals(audience)) {
                audienceMatched = true;
                break;
            }
        }
        if (!audienceMatched) {
            throw new SamlAuthenticationException("Assertion audience does not match this service provider");
        }
    }

    private void validateSubject(Element assertion, HttpServletRequest request) {
        String nameId = extractNameId(assertion);
        if (isBlank(nameId)) {
            throw new SamlAuthenticationException("Assertion subject is missing a NameID");
        }

        Instant now = Instant.now();
        String expectedRecipient = expectedAcsUrl(request);
        boolean validBearerConfirmation = false;

        NodeList confirmations = evaluateNodes(assertion, "./saml:Subject/saml:SubjectConfirmation");
        for (int i = 0; i < confirmations.getLength(); i++) {
            Element confirmation = (Element) confirmations.item(i);
            if (!SUBJECT_CONFIRMATION_BEARER.equals(confirmation.getAttribute("Method"))) {
                continue;
            }
            Element confirmationData = evaluateElement(confirmation, "./saml:SubjectConfirmationData");
            if (confirmationData == null) {
                continue;
            }
            Instant confirmationExpiry = parseOptionalInstant(confirmationData.getAttribute("NotOnOrAfter"));
            if (confirmationExpiry != null && !now.isBefore(confirmationExpiry.plus(CLOCK_SKEW))) {
                continue;
            }
            String recipient = confirmationData.getAttribute("Recipient");
            if (!isBlank(recipient) && !expectedRecipient.equals(recipient)) {
                continue;
            }
            validBearerConfirmation = true;
            break;
        }

        if (!validBearerConfirmation) {
            throw new SamlAuthenticationException("No valid bearer subject confirmation found");
        }
    }

    private void validateSignature(Element signedElement) {
        Element signatureElement = evaluateElement(signedElement, "./ds:Signature");
        if (signatureElement == null) {
            throw new SamlAuthenticationException("Missing XML signature");
        }
        try {
            DOMValidateContext context = new DOMValidateContext(getTrustedCertificate().getPublicKey(), signatureElement);
            context.setProperty("org.jcp.xml.dsig.secureValidation", Boolean.TRUE);
            markIdAttributes(signedElement.getOwnerDocument().getDocumentElement());

            XMLSignature signature = XMLSignatureFactory.getInstance("DOM").unmarshalXMLSignature(context);
            if (!signature.validate(context)) {
                throw new SamlAuthenticationException("SAML signature validation failed");
            }
        } catch (SamlAuthenticationException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new SamlAuthenticationException("SAML signature validation failed", ex);
        }
    }

    private void validateIssuer(String issuer) {
        if (!isBlank(properties.getIdpIssuer())) {
            if (!properties.getIdpIssuer().equals(issuer)) {
                throw new SamlAuthenticationException("SAML issuer does not match the configured IdP issuer");
            }
        }
    }

    private void validateDestination(String destination, HttpServletRequest request) {
        String expected = expectedAcsUrl(request);
        if (!isBlank(destination) && !expected.equals(destination)) {
            throw new SamlAuthenticationException("SAML response destination does not match this ACS URL");
        }
    }

    private String extractNameId(Element assertion) {
        String nameId = evaluateString(assertion, "string(./saml:Subject/saml:NameID)");
        if (isBlank(nameId)) {
            throw new SamlAuthenticationException("Assertion does not contain a NameID");
        }
        return nameId;
    }

    private Map<String, List<String>> extractAttributes(Element assertion) {
        Map<String, List<String>> attributes = new LinkedHashMap<>();
        NodeList attributeNodes = evaluateNodes(assertion, "./saml:AttributeStatement/saml:Attribute");
        for (int i = 0; i < attributeNodes.getLength(); i++) {
            Element attribute = (Element) attributeNodes.item(i);
            String name = !isBlank(attribute.getAttribute("FriendlyName"))
                ? attribute.getAttribute("FriendlyName")
                : attribute.getAttribute("Name");
            if (isBlank(name)) {
                continue;
            }
            List<String> values = new ArrayList<>();
            NodeList valueNodes = evaluateNodes(attribute, "./saml:AttributeValue");
            for (int j = 0; j < valueNodes.getLength(); j++) {
                String text = valueNodes.item(j).getTextContent();
                if (!isBlank(text)) {
                    values.add(text.trim());
                }
            }
            attributes.put(name, List.copyOf(values));
        }
        return Collections.unmodifiableMap(attributes);
    }

    private Collection<? extends GrantedAuthority> extractAuthorities(Map<String, List<String>> attributes) {
        Set<String> roleValues = new LinkedHashSet<>();
        copyAttributeValues(attributes, roleValues, "roles", "role", "groups", "group", "memberOf");

        List<GrantedAuthority> authorities = new ArrayList<>();
        if (roleValues.isEmpty()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_USER"));
            return authorities;
        }

        for (String role : roleValues) {
            String normalized = role.trim();
            if (normalized.isEmpty()) {
                continue;
            }
            if (!normalized.startsWith("ROLE_")) {
                normalized = "ROLE_" + normalized.replace('-', '_').replace(' ', '_').toUpperCase();
            }
            authorities.add(new SimpleGrantedAuthority(normalized));
        }
        if (authorities.isEmpty()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_USER"));
        }
        return authorities;
    }

    private void copyAttributeValues(
        Map<String, List<String>> attributes,
        Set<String> destination,
        String... candidateNames
    ) {
        for (Map.Entry<String, List<String>> entry : attributes.entrySet()) {
            for (String candidate : candidateNames) {
                if (candidate.equalsIgnoreCase(entry.getKey())) {
                    destination.addAll(entry.getValue());
                }
            }
        }
    }

    private void validateReplay(String messageId) {
        cleanupReplayCache();
        if (!isBlank(messageId) && processedIds.containsKey(messageId)) {
            throw new SamlAuthenticationException("Replay detected for SAML response");
        }
    }

    private void registerReplay(String messageId, Instant expiresAt) {
        if (isBlank(messageId)) {
            return;
        }
        cleanupReplayCache();
        Instant existing = processedIds.putIfAbsent(messageId, expiresAt);
        if (existing != null && existing.isAfter(Instant.now())) {
            throw new SamlAuthenticationException("Replay detected for SAML response");
        }
        processedIds.put(messageId, expiresAt);
    }

    private void cleanupReplayCache() {
        Instant now = Instant.now();
        processedIds.entrySet().removeIf(entry -> !entry.getValue().isAfter(now));
    }

    private Instant resolveReplayExpiry(ParsedSamlResponse response) {
        Instant defaultExpiry = Instant.now().plus(DEFAULT_REPLAY_WINDOW);
        Element conditions = evaluateElement(response.assertionElement(), "./saml:Conditions");
        if (conditions == null) {
            return defaultExpiry;
        }
        Instant notOnOrAfter = parseOptionalInstant(conditions.getAttribute("NotOnOrAfter"));
        if (notOnOrAfter == null) {
            return defaultExpiry;
        }
        Instant conditionExpiry = notOnOrAfter.plus(CLOCK_SKEW);
        return conditionExpiry.isAfter(defaultExpiry) ? conditionExpiry : defaultExpiry;
    }

    private X509Certificate getTrustedCertificate() {
        X509Certificate certificate = trustedCertificate;
        if (certificate != null) {
            return certificate;
        }

        String pem = properties.getTrustedCertificate();
        if (isBlank(pem)) {
            throw new SamlAuthenticationException("app.saml.trusted-certificate must be configured");
        }

        try {
            String sanitized = pem
                .replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replaceAll("\\s+", "");
            byte[] certificateBytes = Base64.getDecoder().decode(sanitized.getBytes(StandardCharsets.US_ASCII));
            CertificateFactory certificateFactory = CertificateFactory.getInstance("X.509");
            certificate = (X509Certificate) certificateFactory.generateCertificate(
                new ByteArrayInputStream(certificateBytes));
            trustedCertificate = certificate;
            return certificate;
        } catch (Exception ex) {
            throw new SamlAuthenticationException("Failed to load the configured IdP signing certificate", ex);
        }
    }

    private String expectedAcsUrl(HttpServletRequest request) {
        if (!isBlank(properties.getAcsUrl())) {
            return properties.getAcsUrl();
        }
        return request.getRequestURL().toString();
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private boolean hasDirectSignature(Element element) {
        return evaluateElement(element, "./ds:Signature") != null;
    }

    private void markIdAttributes(Element element) {
        if (element.hasAttribute("ID")) {
            element.setIdAttribute("ID", true);
        }
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child instanceof Element childElement) {
                markIdAttributes(childElement);
            }
        }
    }

    private String requireAttribute(Element element, String attributeName, String message) {
        String value = element.getAttribute(attributeName);
        if (isBlank(value)) {
            throw new SamlAuthenticationException(message);
        }
        return value;
    }

    private Element evaluateElement(Node context, String expression) {
        try {
            return (Element) newXPath().evaluate(expression, context, XPathConstants.NODE);
        } catch (XPathExpressionException ex) {
            throw new SamlAuthenticationException("Failed to evaluate SAML XPath", ex);
        }
    }

    private NodeList evaluateNodes(Node context, String expression) {
        try {
            return (NodeList) newXPath().evaluate(expression, context, XPathConstants.NODESET);
        } catch (XPathExpressionException ex) {
            throw new SamlAuthenticationException("Failed to evaluate SAML XPath", ex);
        }
    }

    private String evaluateString(Node context, String expression) {
        try {
            return newXPath().evaluate(expression, context).trim();
        } catch (XPathExpressionException ex) {
            throw new SamlAuthenticationException("Failed to evaluate SAML XPath", ex);
        }
    }

    private XPath newXPath() {
        XPathFactory factory = XPathFactory.newInstance();
        try {
            factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        } catch (Exception ex) {
            throw new SamlAuthenticationException("Failed to configure XPath securely", ex);
        }
        XPath xpath = factory.newXPath();
        xpath.setNamespaceContext(new SamlNamespaceContext());
        return xpath;
    }

    private Instant parseOptionalInstant(String value) {
        if (isBlank(value)) {
            return null;
        }
        try {
            return Instant.parse(value);
        } catch (DateTimeParseException ex) {
            throw new SamlAuthenticationException("Invalid SAML timestamp: " + value, ex);
        }
    }

    private record ParsedSamlResponse(
        Element responseElement,
        Element assertionElement,
        String responseId,
        String assertionId
    ) {
    }

    private static final class SamlNamespaceContext implements NamespaceContext {

        @Override
        public String getNamespaceURI(String prefix) {
            return switch (prefix) {
                case "samlp" -> SAML_PROTOCOL_NS;
                case "saml" -> SAML_ASSERTION_NS;
                case "ds" -> XMLSignature.XMLNS;
                case XMLConstants.DEFAULT_NS_PREFIX -> XMLConstants.NULL_NS_URI;
                default -> XMLConstants.NULL_NS_URI;
            };
        }

        @Override
        public String getPrefix(String namespaceURI) {
            return switch (namespaceURI) {
                case SAML_PROTOCOL_NS -> "samlp";
                case SAML_ASSERTION_NS -> "saml";
                case XMLSignature.XMLNS -> "ds";
                default -> null;
            };
        }

        @Override
        public Iterator<String> getPrefixes(String namespaceURI) {
            String prefix = getPrefix(namespaceURI);
            return prefix == null ? Collections.emptyIterator() : List.of(prefix).iterator();
        }
    }
}