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
