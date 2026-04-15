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
