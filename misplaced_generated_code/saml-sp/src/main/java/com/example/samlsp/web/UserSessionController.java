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
