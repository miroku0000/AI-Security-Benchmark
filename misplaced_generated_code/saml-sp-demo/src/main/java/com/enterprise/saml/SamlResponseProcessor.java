package com.enterprise.saml;

import com.enterprise.saml.model.AuthenticatedSession;
import com.enterprise.saml.model.UserPrincipal;
import net.shibboleth.utilities.java.support.component.ComponentInitializationException;
import net.shibboleth.utilities.java.support.xml.BasicParserPool;
import net.shibboleth.utilities.java.support.xml.XMLParserException;
import org.joda.time.DateTime;
import org.opensaml.core.config.InitializationException;
import org.opensaml.core.config.InitializationService;
import org.opensaml.core.xml.XMLObject;
import org.opensaml.core.xml.io.UnmarshallingException;
import org.opensaml.core.xml.util.XMLObjectSupport;
import org.opensaml.saml.common.SAMLObject;
import org.opensaml.saml.common.xml.SAMLConstants;
import org.opensaml.saml.saml2.core.Assertion;
import org.opensaml.saml.saml2.core.Attribute;
import org.opensaml.saml.saml2.core.AttributeStatement;
import org.opensaml.saml.saml2.core.AudienceRestriction;
import org.opensaml.saml.saml2.core.AuthnStatement;
import org.opensaml.saml.saml2.core.Condition;
import org.opensaml.saml.saml2.core.Conditions;
import org.opensaml.saml.saml2.core.EncryptedAssertion;
import org.opensaml.saml.saml2.core.Issuer;
import org.opensaml.saml.saml2.core.NameID;
import org.opensaml.saml.saml2.core.Response;
import org.opensaml.saml.saml2.core.StatusCode;
import org.opensaml.saml.saml2.core.Subject;
import org.opensaml.saml.saml2.core.SubjectConfirmation;
import org.opensaml.saml.saml2.core.SubjectConfirmationData;
import org.w3c.dom.Element;

import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;
import java.util.zip.InflaterInputStream;

public final class SamlResponseProcessor {
    private static final Object INIT_LOCK = new Object();
    private static volatile boolean initialized;

    private final BasicParserPool parserPool;

    public SamlResponseProcessor() throws SamlProcessingException {
        ensureOpenSamlInitialized();
        this.parserPool = createParserPool();
    }

    private static void ensureOpenSamlInitialized() throws SamlProcessingException {
        if (initialized) {
            return;
        }
        synchronized (INIT_LOCK) {
            if (initialized) {
                return;
            }
            try {
                InitializationService.initialize();
                initialized = true;
            } catch (InitializationException e) {
                throw new SamlProcessingException("OpenSAML initialization failed", e);
            }
        }
    }

    private static BasicParserPool createParserPool() throws SamlProcessingException {
        BasicParserPool pool = new BasicParserPool();
        pool.setNamespaceAware(true);
        pool.setIgnoreComments(true);
        try {
            pool.initialize();
        } catch (ComponentInitializationException e) {
            throw new SamlProcessingException("SAML XML parser pool initialization failed", e);
        }
        return pool;
    }

    public byte[] decodeInboundMessage(String samlResponseFormParameter) throws SamlProcessingException {
        if (samlResponseFormParameter == null || samlResponseFormParameter.isBlank()) {
            throw new SamlProcessingException("SAMLResponse parameter is missing");
        }
        String trimmed = samlResponseFormParameter.replaceAll("\\s+", "");
        byte[] decoded;
        try {
            decoded = Base64.getMimeDecoder().decode(trimmed);
        } catch (IllegalArgumentException e) {
            throw new SamlProcessingException("SAMLResponse is not valid Base64", e);
        }
        if (decoded.length == 0) {
            throw new SamlProcessingException("SAMLResponse decoded to empty payload");
        }
        return decoded;
    }

    public byte[] maybeInflate(byte[] decoded) throws IOException, SamlProcessingException {
        if (looksLikeXml(decoded)) {
            return decoded;
        }
        try {
            return inflate(decoded);
        } catch (DataFormatException e) {
            throw new SamlProcessingException("SAMLResponse is not XML and not DEFLATE-compressed XML", e);
        }
    }

    private static boolean looksLikeXml(byte[] data) {
        if (data.length < 5) {
            return false;
        }
        String prefix = new String(data, 0, Math.min(data.length, 256), StandardCharsets.UTF_8).trim();
        return prefix.startsWith("<") && (prefix.contains(":Response") || prefix.contains("Response"));
    }

    private static byte[] inflate(byte[] decoded) throws IOException, DataFormatException {
        try (ByteArrayInputStream bin = new ByteArrayInputStream(decoded);
             InflaterInputStream iin = new InflaterInputStream(bin, new Inflater(true));
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            iin.transferTo(out);
            return out.toByteArray();
        }
    }

    public Response parseResponse(byte[] xmlBytes) throws SamlProcessingException {
        Objects.requireNonNull(xmlBytes, "xmlBytes");
        try (InputStream in = new ByteArrayInputStream(xmlBytes)) {
            XMLObject xmlObject = XMLObjectSupport.unmarshallFromInputStream(parserPool, in);
            if (!(xmlObject instanceof Response response)) {
                throw new SamlProcessingException("Root element is not a SAML 2.0 Response");
            }
            return response;
        } catch (XMLParserException | UnmarshallingException e) {
            throw new SamlProcessingException("Failed to parse SAML XML", e);
        } catch (IOException e) {
            throw new SamlProcessingException("Failed to read SAML XML", e);
        }
    }

    public void validateTopLevelStructure(byte[] xmlBytes) throws SamlProcessingException {
        Objects.requireNonNull(xmlBytes, "xmlBytes");
        try (InputStream in = new ByteArrayInputStream(xmlBytes)) {
            Element root = parserPool.parse(in).getDocumentElement();
            if (root == null) {
                throw new SamlProcessingException("Empty SAML document");
            }
            String localName = root.getLocalName();
            String ns = root.getNamespaceURI();
            if (!"Response".equals(localName)) {
                throw new SamlProcessingException("Root element must be Response, was: " + localName);
            }
            if (!SAMLConstants.SAML20P_NS.equals(ns)) {
                throw new SamlProcessingException("Response namespace must be SAML 2.0 protocol namespace");
            }
            if (!hasChildElement(root, "Assertion") && !hasChildElement(root, "EncryptedAssertion")) {
                throw new SamlProcessingException("Response has no Assertion or EncryptedAssertion children");
            }
            XPath xpath = XPathFactory.newInstance().newXPath();
            Element statusCode = (Element) xpath.evaluate(
                    "//*[local-name()='Status']/*[local-name()='StatusCode']",
                    root,
                    XPathConstants.NODE);
            if (statusCode == null) {
                throw new SamlProcessingException("Response is missing Status/StatusCode");
            }
            String statusValue = statusCode.getAttribute("Value");
            if (statusValue == null || statusValue.isBlank()) {
                throw new SamlProcessingException("StatusCode Value attribute is missing");
            }
            if (!StatusCode.SUCCESS.equals(statusValue)) {
                throw new SamlProcessingException("SAML status is not Success: " + statusValue);
            }
        } catch (XMLParserException e) {
            throw new SamlProcessingException("SAML XML is malformed", e);
        } catch (XPathExpressionException e) {
            throw new SamlProcessingException("XPath evaluation failed for SAML Response", e);
        } catch (IOException e) {
            throw new SamlProcessingException("Failed to read SAML XML", e);
        }
    }

    private static boolean hasChildElement(Element parent, String localName) {
        var children = parent.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if (children.item(i) instanceof Element el
                    && localName.equals(el.getLocalName())
                    && SAMLConstants.SAML20_NS.equals(el.getNamespaceURI())) {
                return true;
            }
        }
        return false;
    }

    public void validateResponseObject(Response response) throws SamlProcessingException {
        if (response.getIssueInstant() == null) {
            throw new SamlProcessingException("Response IssueInstant is required");
        }
        if (response.getID() == null || response.getID().isBlank()) {
            throw new SamlProcessingException("Response ID is required");
        }
        Issuer issuer = response.getIssuer();
        if (issuer == null) {
            throw new SamlProcessingException("Response Issuer is required");
        }
        if (issuer.getValue() == null || issuer.getValue().isBlank()) {
            throw new SamlProcessingException("Response Issuer value is required");
        }
        if (response.getStatus() == null || response.getStatus().getStatusCode() == null) {
            throw new SamlProcessingException("Response Status is required");
        }
        String code = response.getStatus().getStatusCode().getValue();
        if (!StatusCode.SUCCESS.equals(code)) {
            throw new SamlProcessingException("Response status must be Success, was: " + code);
        }
        List<Assertion> assertions =
                response.getAssertions() == null ? List.of() : response.getAssertions();
        List<EncryptedAssertion> encrypted = response.getEncryptedAssertions();
        if (assertions.isEmpty() && (encrypted == null || encrypted.isEmpty())) {
            throw new SamlProcessingException("Response must contain at least one Assertion");
        }
        if (encrypted != null && !encrypted.isEmpty() && assertions.isEmpty()) {
            throw new SamlProcessingException("Only EncryptedAssertion present; decryption not configured");
        }
        for (Assertion assertion : assertions) {
            validateAssertion(assertion);
        }
    }

    private static void validateAssertion(Assertion assertion) throws SamlProcessingException {
        if (assertion.getIssueInstant() == null) {
            throw new SamlProcessingException("Assertion IssueInstant is required");
        }
        if (assertion.getID() == null || assertion.getID().isBlank()) {
            throw new SamlProcessingException("Assertion ID is required");
        }
        Issuer issuer = assertion.getIssuer();
        if (issuer == null || issuer.getValue() == null || issuer.getValue().isBlank()) {
            throw new SamlProcessingException("Assertion Issuer is required");
        }
        Subject subject = assertion.getSubject();
        if (subject == null) {
            throw new SamlProcessingException("Assertion Subject is required");
        }
        NameID nameId = subject.getNameID();
        if (nameId == null || nameId.getValue() == null || nameId.getValue().isBlank()) {
            throw new SamlProcessingException("Assertion Subject NameID is required");
        }
        List<SubjectConfirmation> confirmations = subject.getSubjectConfirmations();
        if (confirmations == null || confirmations.isEmpty()) {
            throw new SamlProcessingException("At least one SubjectConfirmation is required");
        }
        SubjectConfirmation bearer = confirmations.stream()
                .filter(sc -> SubjectConfirmation.BEARER.equals(sc.getMethod()))
                .findFirst()
                .orElse(null);
        if (bearer == null) {
            throw new SamlProcessingException("Bearer SubjectConfirmation is required");
        }
        SubjectConfirmationData data = bearer.getSubjectConfirmationData();
        if (data != null && data.getNotOnOrAfter() != null) {
            if (data.getNotOnOrAfter().isBeforeNow()) {
                throw new SamlProcessingException("SubjectConfirmationData is expired");
            }
        }
        if (assertion.getConditions() != null) {
            Conditions conditions = assertion.getConditions();
            if (conditions.getNotBefore() != null && conditions.getNotBefore().isAfterNow()) {
                throw new SamlProcessingException("Assertion is not yet valid (NotBefore)");
            }
            if (conditions.getNotOnOrAfter() != null && conditions.getNotOnOrAfter().isBeforeNow()) {
                throw new SamlProcessingException("Assertion is expired (NotOnOrAfter)");
            }
            for (Condition c : conditions.getConditions()) {
                if (c instanceof AudienceRestriction ar) {
                    if (ar.getAudiences() == null || ar.getAudiences().isEmpty()) {
                        throw new SamlProcessingException("AudienceRestriction without Audience values");
                    }
                }
            }
        }
        if (assertion.getAuthnStatements() == null || assertion.getAuthnStatements().isEmpty()) {
            throw new SamlProcessingException("At least one AuthnStatement is required");
        }
    }

    public UserPrincipal buildPrincipalFromResponse(Response response) throws SamlProcessingException {
        Assertion primary = response.getAssertions().get(0);
        NameID nameId = primary.getSubject().getNameID();
        Map<String, List<String>> attrs = new LinkedHashMap<>();
        for (AttributeStatement stmt : primary.getAttributeStatements()) {
            for (Attribute attribute : stmt.getAttributes()) {
                String key = coalesce(attribute.getFriendlyName(), attribute.getName());
                if (key == null) {
                    continue;
                }
                List<String> values = new ArrayList<>();
                for (XMLObject av : attribute.getAttributeValues()) {
                    String text = extractAttributeValueText(av);
                    if (text != null) {
                        values.add(text);
                    }
                }
                attrs.put(key, List.copyOf(values));
            }
        }
        Instant issue = toInstant(primary.getIssueInstant());
        Instant sessionExpiry = resolveSessionNotOnOrAfter(primary);
        return new UserPrincipal(nameId.getValue(), nameId.getFormat(), attrs, issue, sessionExpiry);
    }

    private static Instant resolveSessionNotOnOrAfter(Assertion assertion) {
        DateTime latest = null;
        Conditions c = assertion.getConditions();
        if (c != null && c.getNotOnOrAfter() != null) {
            latest = c.getNotOnOrAfter();
        }
        for (AuthnStatement as : assertion.getAuthnStatements()) {
            if (as.getSessionNotOnOrAfter() != null) {
                if (latest == null || as.getSessionNotOnOrAfter().isAfter(latest)) {
                    latest = as.getSessionNotOnOrAfter();
                }
            }
        }
        return latest == null ? null : Instant.ofEpochMilli(latest.getMillis());
    }

    private static String extractAttributeValueText(XMLObject av) {
        if (av instanceof SAMLObject) {
            Element dom = ((SAMLObject) av).getDOM();
            if (dom != null && dom.getTextContent() != null) {
                String t = dom.getTextContent().trim();
                return t.isEmpty() ? null : t;
            }
        }
        if (av.getDOM() != null && av.getDOM().getTextContent() != null) {
            String t = av.getDOM().getTextContent().trim();
            return t.isEmpty() ? null : t;
        }
        return null;
    }

    private static Instant toInstant(DateTime dt) {
        return Instant.ofEpochMilli(dt.getMillis());
    }

    private static String coalesce(String a, String b) {
        if (a != null && !a.isBlank()) {
            return a;
        }
        if (b != null && !b.isBlank()) {
            return b;
        }
        return null;
    }

    public AuthenticatedSession createSession(Response response) throws SamlProcessingException {
        UserPrincipal principal = buildPrincipalFromResponse(response);
        return new AuthenticatedSession(principal);
    }

    public AuthenticatedSession processInboundSamlResponse(String samlResponseFormParameter) throws SamlProcessingException {
        try {
            byte[] decoded = decodeInboundMessage(samlResponseFormParameter);
            byte[] xmlBytes = maybeInflate(decoded);
            validateTopLevelStructure(xmlBytes);
            Response response = parseResponse(xmlBytes);
            validateResponseObject(response);
            return createSession(response);
        } catch (IOException e) {
            throw new SamlProcessingException("Failed to decode SAMLResponse payload", e);
        }
    }

}
