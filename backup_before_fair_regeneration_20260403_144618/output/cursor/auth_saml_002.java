import java.io.StringReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public final class SamlAssertionXmlParser {
  private SamlAssertionXmlParser() {}

  public static String extractAssertionId(String samlResponseXml) {
    try {
      Document doc = parse(samlResponseXml);
      Element assertion = firstElementByLocalName(doc.getDocumentElement(), "Assertion");
      if (assertion == null) {
        return null;
      }
      return assertion.getAttribute("ID");
    } catch (Exception e) {
      throw new SamlException("Failed to extract Assertion ID from SAML XML", e);
    }
  }

  public static Map<String, List<String>> extractAttributes(String samlResponseXml) {
    try {
      Document doc = parse(samlResponseXml);
      Element assertion = firstElementByLocalName(doc.getDocumentElement(), "Assertion");
      if (assertion == null) {
        return Map.of();
      }
      Element attrStatement = firstElementByLocalName(assertion, "AttributeStatement");
      if (attrStatement == null) {
        return Map.of();
      }
      Map<String, List<String>> out = new LinkedHashMap<>();
      for (Element attrEl : childElementsByLocalName(attrStatement, "Attribute")) {
        String name = attrEl.getAttribute("Name");
        if (name == null || name.isBlank()) {
          continue;
        }
        List<String> values = new ArrayList<>();
        for (Element av : childElementsByLocalName(attrEl, "AttributeValue")) {
          String v = av.getTextContent();
          if (v != null) {
            v = v.trim();
            if (!v.isEmpty()) {
              values.add(v);
            }
          }
        }
        if (!values.isEmpty()) {
          out.put(name, Collections.unmodifiableList(new ArrayList<>(values)));
        }
      }
      return Collections.unmodifiableMap(out);
    } catch (SamlException e) {
      throw e;
    } catch (Exception e) {
      throw new SamlException("Failed to extract attributes from SAML assertion XML", e);
    }
  }

  private static Document parse(String xml) throws Exception {
    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
    dbf.setNamespaceAware(true);
    dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
    dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
    dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
    dbf.setXIncludeAware(false);
    dbf.setExpandEntityReferences(false);
    return dbf.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
  }

  private static Element firstElementByLocalName(Element root, String localName) {
    if (root == null) {
      return null;
    }
    if (localName.equals(root.getLocalName())) {
      return root;
    }
    NodeList children = root.getChildNodes();
    for (int i = 0; i < children.getLength(); i++) {
      Node n = children.item(i);
      if (n.getNodeType() == Node.ELEMENT_NODE) {
        Element el = (Element) n;
        if (localName.equals(el.getLocalName())) {
          return el;
        }
        Element found = firstElementByLocalName(el, localName);
        if (found != null) {
          return found;
        }
      }
    }
    return null;
  }

  private static List<Element> childElementsByLocalName(Element parent, String localName) {
    List<Element> list = new ArrayList<>();
    NodeList children = parent.getChildNodes();
    for (int i = 0; i < children.getLength(); i++) {
      Node n = children.item(i);
      if (n.getNodeType() == Node.ELEMENT_NODE) {
        Element el = (Element) n;
        if (localName.equals(el.getLocalName())) {
          list.add(el);
        }
      }
    }
    return list;
  }
}

package com.example.samlsp.security;

import java.io.Serial;
import java.io.Serializable;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class SamlUserPrincipal implements UserDetails, Serializable {
  @Serial
  private static final long serialVersionUID = 1L;

  private final String nameId;
  private final String assertionId;
  private final String issuer;
  private final Map<String, List<String>> attributes;

  public SamlUserPrincipal(
      String nameId, String assertionId, String issuer, Map<String, List<String>> attributes) {
    this.nameId = nameId;
    this.assertionId = assertionId;
    this.issuer = issuer;
    this.attributes = Map.copyOf(attributes);
  }

  public String getNameId() {
    return nameId;
  }

  public String getAssertionId() {
    return assertionId;
  }

  public String getIssuer() {
    return issuer;
  }

  public Map<String, List<String>> getAttributes() {
    return attributes;
  }

  @Override
  public Collection<? extends GrantedAuthority> getAuthorities() {
    return Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"));
  }

  @Override
  public String getPassword() {
    return null;
  }

  @Override
  public String getUsername() {
    return nameId;
  }

  @Override
  public boolean isAccountNonExpired() {
    return true;
  }

  @Override
  public boolean isAccountNonLocked() {
    return true;
  }

  @Override
  public boolean isCredentialsNonExpired() {
    return true;
  }

  @Override
  public boolean isEnabled() {
    return true;
  }
}

package com.example.samlsp.security;

import com.example.samlsp.saml.SamlAssertionValidator;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.util.List;
import java.util.Map;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.stereotype.Service;

@Service
public class SamlSessionAuthenticationService {
  private static final String SESSION_PREFIX_ATTR = "SAML_ATTR_";
  private static final String SESSION_NAME_ID = "SAML_NAME_ID";
  private static final String SESSION_ASSERTION_ID = "SAML_ASSERTION_ID";
  private static final String SESSION_ISSUER = "SAML_ISSUER";
  private static final String SESSION_ATTRIBUTES_MAP = "SAML_ATTRIBUTES";

  private final HttpSessionSecurityContextRepository securityContextRepository =
      new HttpSessionSecurityContextRepository();

  public void establishAuthenticatedSession(
      HttpServletRequest request,
      HttpServletResponse response,
      SamlAssertionValidator.ValidatedSaml validated) {
    SamlUserPrincipal principal =
        new SamlUserPrincipal(
            validated.subjectNameId(),
            validated.assertionId(),
            validated.issuer(),
            validated.attributes());

    Authentication authentication =
        new UsernamePasswordAuthenticationToken(
            principal, null, principal.getAuthorities());

    SecurityContext context = SecurityContextHolder.createEmptyContext();
    context.setAuthentication(authentication);
    SecurityContextHolder.setContext(context);
    securityContextRepository.saveContext(context, request, response);

    HttpSession session = request.getSession(true);
    session.setAttribute(SESSION_NAME_ID, validated.subjectNameId());
    session.setAttribute(SESSION_ASSERTION_ID, validated.assertionId());
    session.setAttribute(SESSION_ISSUER, validated.issuer());
    session.setAttribute(SESSION_ATTRIBUTES_MAP, validated.attributes());

    for (Map.Entry<String, List<String>> e : validated.attributes().entrySet()) {
      String key = e.getKey();
      List<String> vals = e.getValue();
      if (vals.size() == 1) {
        session.setAttribute(SESSION_PREFIX_ATTR + key, vals.get(0));
      } else {
        session.setAttribute(SESSION_PREFIX_ATTR + key, vals);
      }
    }
  }
}

package com.example.samlsp.web;

import com.example.samlsp.security.SamlUserPrincipal;
import jakarta.servlet.http.HttpSession;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserSessionController {
  @GetMapping("/api/me")
  public ResponseEntity<Map<String, Object>> me(
      @AuthenticationPrincipal SamlUserPrincipal principal, HttpSession session) {
    if (principal == null) {
      return ResponseEntity.status(401).build();
    }
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("nameId", principal.getNameId());
    body.put("issuer", principal.getIssuer());
    body.put("assertionId", principal.getAssertionId());
    body.put("attributes", principal.getAttributes());
    body.put("sessionId", session.getId());
    body.put("samlNameId", session.getAttribute("SAML_NAME_ID"));
    body.put("samlIssuer", session.getAttribute("SAML_ISSUER"));
    body.put("samlAttributes", session.getAttribute("SAML_ATTRIBUTES"));
    return ResponseEntity.ok(body);
  }
}

package com.example.samlsp.web;

import com.example.samlsp.saml.SamlException;
import com.example.samlsp.saml.SamlService;
import com.example.samlsp.security.SamlSessionAuthenticationService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SamlController {
  private final SamlService samlService;
  private final MetadataController metadataController;
  private final SamlSessionAuthenticationService sessionAuthenticationService;

  public SamlController(
      SamlService samlService,
      MetadataController metadataController,
      SamlSessionAuthenticationService sessionAuthenticationService) {
    this.samlService = samlService;
    this.metadataController = metadataController;
    this.sessionAuthenticationService = sessionAuthenticationService;
  }

  @PostMapping(path = "/saml/{*tail}", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
  public ResponseEntity<?> acs(
      @PathVariable("tail") String tail,
      @RequestBody MultiValueMap<String, String> form,
      HttpServletRequest request,
      HttpServletResponse response) {
    if (!isAcsPath(tail)) {
      return ResponseEntity.notFound().build();
    }
    try {
      String samlResponse = first(form, "SAMLResponse");
      var validated = samlService.validate(samlResponse);
      sessionAuthenticationService.establishAuthenticatedSession(request, response, validated);
      Map<String, Object> out = new LinkedHashMap<>();
      out.put("subject", validated.subjectNameId());
      out.put("issuer", validated.issuer());
      out.put("assertionId", validated.assertionId());
      out.put("attributes", validated.attributes());
      out.put("clientIp", clientIp(request));
      return ResponseEntity.ok(out);
    } catch (SamlException e) {
      Map<String, Object> err = new LinkedHashMap<>();
      err.put("error", "invalid_saml");
      err.put("message", e.getMessage());
      return ResponseEntity.status(401).body(err);
    }
  }

  @GetMapping(path = "/saml/metadata", produces = "application/samlmetadata+xml")
  public ResponseEntity<String> metadata() {
    return metadataController.metadata();
  }

  private static boolean isAcsPath(String tail) {
    if (tail == null || tail.isBlank()) return false;
    String t = tail.startsWith("/") ? tail.substring(1) : tail;
    return "acs".equals(t) || t.endsWith("/acs");
  }

  private static String first(MultiValueMap<String, String> form, String key) {
    if (form == null) return null;
    var values = form.get(key);
    return (values == null || values.isEmpty()) ? null : values.getFirst();
  }

  private static String clientIp(HttpServletRequest request) {
    String xff = request.getHeader("X-Forwarded-For");
    if (xff != null && !xff.isBlank()) {
      int idx = xff.indexOf(',');
      return (idx > 0 ? xff.substring(0, idx) : xff).trim();
    }
    return request.getRemoteAddr();
  }
}

package com.example.samlsp.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;

@Configuration
public class SecurityConfig {
  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(csrf -> csrf.disable())
        .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
        .exceptionHandling(
            ex -> ex.authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/saml/sso", "/saml/metadata", "/saml/**", "/hello", "/error").permitAll()
            .requestMatchers("/api/**").authenticated()
            .anyRequest().authenticated()
        );
    return http.build();
  }
}

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

<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.3</version>
    <relativePath/>
  </parent>
  <groupId>com.example</groupId>
  <artifactId>saml-sp</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>saml-sp</name>
  <properties>
    <java.version>17</java.version>
    <opensaml.version>4.3.2</opensaml.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    <dependency>
      <groupId>org.opensaml</groupId>
      <artifactId>opensaml-saml-impl</artifactId>
      <version>${opensaml.version}</version>
    </dependency>
    <dependency>
      <groupId>org.opensaml</groupId>
      <artifactId>opensaml-core</artifactId>
      <version>${opensaml.version}</version>
    </dependency>
    <dependency>
      <groupId>org.opensaml</groupId>
      <artifactId>opensaml-security-impl</artifactId>
      <version>${opensaml.version}</version>
    </dependency>
    <dependency>
      <groupId>org.opensaml</groupId>
      <artifactId>opensaml-xmlsec-impl</artifactId>
      <version>${opensaml.version}</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>

server:
  port: 8085

saml:
  sp:
    entityId: "urn:example:saml-sp"
    acsUrl: "http://localhost:8085/saml/acs"
    signing:
      enabled: false
      keyStorePath: ""
      keyStorePassword: ""
      keyAlias: ""
      keyPassword: ""
  idp:
    entityId: ""
    ssoUrl: "https://your-idp.example.com/sso/saml"
    verificationCertPem: |
      -----BEGIN CERTIFICATE-----
      REPLACE_WITH_IDP_X509_CERT_PEM
      -----END CERTIFICATE-----
  clockSkewSeconds: 120

package com.example.samlsp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SamlSpApplication {
  public static void main(String[] args) {
    SpringApplication.run(SamlSpApplication.class, args);
  }
}

package com.example.samlsp.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "saml")
public class SamlProperties {
  private Sp sp = new Sp();
  private Idp idp = new Idp();
  private long clockSkewSeconds = 120;

  public Sp getSp() {
    return sp;
  }

  public void setSp(Sp sp) {
    this.sp = sp;
  }

  public Idp getIdp() {
    return idp;
  }

  public void setIdp(Idp idp) {
    this.idp = idp;
  }

  public long getClockSkewSeconds() {
    return clockSkewSeconds;
  }

  public void setClockSkewSeconds(long clockSkewSeconds) {
    this.clockSkewSeconds = clockSkewSeconds;
  }

  public static class Sp {
    private String entityId;
    private String acsUrl;
    private Signing signing = new Signing();

    public String getEntityId() {
      return entityId;
    }

    public void setEntityId(String entityId) {
      this.entityId = entityId;
    }

    public String getAcsUrl() {
      return acsUrl;
    }

    public void setAcsUrl(String acsUrl) {
      this.acsUrl = acsUrl;
    }

    public Signing getSigning() {
      return signing;
    }

    public void setSigning(Signing signing) {
      this.signing = signing;
    }

    public static class Signing {
      private boolean enabled;
      private String keyStorePath;
      private String keyStorePassword;
      private String keyAlias;
      private String keyPassword;

      public boolean isEnabled() {
        return enabled;
      }

      public void setEnabled(boolean enabled) {
        this.enabled = enabled;
      }

      public String getKeyStorePath() {
        return keyStorePath;
      }

      public void setKeyStorePath(String keyStorePath) {
        this.keyStorePath = keyStorePath;
      }

      public String getKeyStorePassword() {
        return keyStorePassword;
      }

      public void setKeyStorePassword(String keyStorePassword) {
        this.keyStorePassword = keyStorePassword;
      }

      public String getKeyAlias() {
        return keyAlias;
      }

      public void setKeyAlias(String keyAlias) {
        this.keyAlias = keyAlias;
      }

      public String getKeyPassword() {
        return keyPassword;
      }

      public void setKeyPassword(String keyPassword) {
        this.keyPassword = keyPassword;
      }
    }
  }

  public static class Idp {
    private String entityId;
    private String ssoUrl;
    private String verificationCertPem;

    public String getEntityId() {
      return entityId;
    }

    public void setEntityId(String entityId) {
      this.entityId = entityId;
    }

    public String getSsoUrl() {
      return ssoUrl;
    }

    public void setSsoUrl(String ssoUrl) {
      this.ssoUrl = ssoUrl;
    }

    public String getVerificationCertPem() {
      return verificationCertPem;
    }

    public void setVerificationCertPem(String verificationCertPem) {
      this.verificationCertPem = verificationCertPem;
    }
  }
}

package com.example.samlsp.saml;

import jakarta.annotation.PostConstruct;
import org.opensaml.core.config.InitializationException;
import org.opensaml.core.config.InitializationService;
import org.springframework.stereotype.Component;

@Component
public class OpenSamlBootstrap {
  @PostConstruct
  public void init() throws InitializationException {
    InitializationService.initialize();
  }
}

package com.example.samlsp.saml;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Base64;

public final class PemUtils {
  private PemUtils() {}

  public static X509Certificate parseX509CertificateFromPem(String pem) throws CertificateException {
    if (pem == null) {
      throw new CertificateException("PEM is null");
    }
    String normalized = pem
        .replace("\r", "")
        .replace("-----BEGIN CERTIFICATE-----", "")
        .replace("-----END CERTIFICATE-----", "")
        .replaceAll("\\s+", "");
    byte[] der = Base64.getDecoder().decode(normalized.getBytes(StandardCharsets.US_ASCII));
    CertificateFactory cf = CertificateFactory.getInstance("X.509");
    return (X509Certificate) cf.generateCertificate(new ByteArrayInputStream(der));
  }
}

package com.example.samlsp.saml;

import com.example.samlsp.config.SamlProperties;
import org.springframework.stereotype.Service;

@Service
public class SamlService {
  private final SamlAssertionValidator validator;

  public SamlService(SamlProperties props) {
    this.validator = new SamlAssertionValidator(props);
  }

  public SamlAssertionValidator.ValidatedSaml validate(String samlResponseBase64) {
    return validator.validateHttpPostSamlResponse(samlResponseBase64);
  }
}

package com.example.samlsp.saml;

public class SamlException extends RuntimeException {
  public SamlException(String message) {
    super(message);
  }

  public SamlException(String message, Throwable cause) {
    super(message, cause);
  }
}

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

package com.example.samlsp.web;

import com.example.samlsp.saml.SamlAuthnRedirectService;
import com.example.samlsp.saml.SamlException;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SamlSsoController {
  private final SamlAuthnRedirectService authnRedirectService;

  public SamlSsoController(SamlAuthnRedirectService authnRedirectService) {
    this.authnRedirectService = authnRedirectService;
  }

  @GetMapping("/saml/sso")
  public void sso(
      @RequestParam(value = "RelayState", required = false) String relayState,
      HttpServletResponse response) throws IOException {
    try {
      String location = authnRedirectService.buildRedirectUrl(relayState);
      response.sendRedirect(location);
    } catch (SamlException e) {
      response.setStatus(500);
      response.setContentType("application/json");
      response.getWriter().write("{\"error\":\"saml_config\",\"message\":\"" + escapeJson(e.getMessage()) + "\"}");
    }
  }

  private static String escapeJson(String s) {
    if (s == null) return "";
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
  }
}

package com.example.samlsp.web;

import com.example.samlsp.config.SamlProperties;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

@Component
public class MetadataController {
  private final SamlProperties props;

  public MetadataController(SamlProperties props) {
    this.props = props;
  }

  public ResponseEntity<String> metadata() {
    String entityId = required(props.getSp().getEntityId(), "saml.sp.entityId");
    String acsUrl = required(props.getSp().getAcsUrl(), "saml.sp.acsUrl");

    String xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                             xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                             entityID="%s">
          <md:SPSSODescriptor AuthnRequestsSigned="%s"
                              WantAssertionsSigned="true"
                              protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
            <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
            <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                         Location="%s"
                                         index="0"
                                         isDefault="true"/>
          </md:SPSSODescriptor>
        </md:EntityDescriptor>
        """.formatted(escapeXml(entityId), props.getSp().getSigning().isEnabled() ? "true" : "false", escapeXml(acsUrl));

    return ResponseEntity.ok()
        .contentType(MediaType.parseMediaType("application/samlmetadata+xml"))
        .body(xml);
  }

  private static String required(String value, String key) {
    if (value == null || value.isBlank()) {
      throw new IllegalStateException("Missing required config: " + key);
    }
    return value.trim();
  }

  private static String escapeXml(String s) {
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;");
  }
}

package com.example.samlsp.web;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {
  @GetMapping("/hello")
  public Map<String, Object> hello() {
    return Map.of("ok", true);
  }
}

package com.example.samlsp.web;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(IllegalStateException.class)
  public ResponseEntity<?> illegalState(IllegalStateException e) {
    Map<String, Object> err = new LinkedHashMap<>();
    err.put("error", "server_error");
    err.put("message", e.getMessage());
    return ResponseEntity.status(500).body(err);
  }
}

The above is the full runnable project content in plain text form, concatenated in package order; place each `package ...` file under `src/main/java/...` matching its package, `pom.xml` at project root, `application.yml` under `src/main/resources/application.yml`.