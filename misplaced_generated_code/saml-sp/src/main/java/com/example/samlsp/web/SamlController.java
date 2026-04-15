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

