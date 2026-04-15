package com.example.oidcclient;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.OAuth2AuthorizedClient;
import org.springframework.security.oauth2.client.OAuth2AuthorizedClientService;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.web.authentication.SavedRequestAwareAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

@Component
public class OidcSessionAuthenticationSuccessHandler extends SavedRequestAwareAuthenticationSuccessHandler {

  private static final String SESSION_USER = "user";

  private final OAuth2AuthorizedClientService authorizedClientService;

  public OidcSessionAuthenticationSuccessHandler(OAuth2AuthorizedClientService authorizedClientService) {
    this.authorizedClientService = authorizedClientService;
    setDefaultTargetUrl("/");
    setAlwaysUseDefaultTargetUrl(true);
  }

  @Override
  public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response, Authentication authentication)
      throws ServletException, IOException {
    if (authentication instanceof OAuth2AuthenticationToken token && token.getPrincipal() instanceof OidcUser oidcUser) {
      String accessToken = resolveAccessTokenValue(token);
      Map<String, Object> idClaims = new LinkedHashMap<>(oidcUser.getIdToken().getClaims());
      idClaims.remove("nonce");
      Map<String, Object> userInfoClaims = new LinkedHashMap<>();
      if (oidcUser.getUserInfo() != null) {
        userInfoClaims.putAll(oidcUser.getUserInfo().getClaims());
      }
      UserSession sessionUser =
          new UserSession(
              oidcUser.getSubject(),
              issuer(oidcUser.getIdToken()),
              firstNonBlank(oidcUser.getEmail(), stringClaim(userInfoClaims, "email")),
              firstNonBlank(oidcUser.getFullName(), stringClaim(userInfoClaims, "name")),
              oidcUser.getIdToken().getIssuedAt(),
              oidcUser.getIdToken().getExpiresAt(),
              idClaims,
              userInfoClaims,
              accessToken);
      request.getSession(true).setAttribute(SESSION_USER, sessionUser);
    }
    super.onAuthenticationSuccess(request, response, authentication);
  }

  private String resolveAccessTokenValue(OAuth2AuthenticationToken token) {
    OAuth2AuthorizedClient client =
        authorizedClientService.loadAuthorizedClient(
            token.getAuthorizedClientRegistrationId(), token.getName());
    if (client == null || client.getAccessToken() == null) {
      return null;
    }
    return client.getAccessToken().getTokenValue();
  }

  private static String stringClaim(Map<String, Object> claims, String key) {
    Object v = claims.get(key);
    return v == null ? null : String.valueOf(v);
  }

  private static String issuer(OidcIdToken idToken) {
    Object iss = idToken.getClaims().get("iss");
    return iss == null ? null : String.valueOf(iss);
  }

  private static String firstNonBlank(String a, String b) {
    if (a != null && !a.isBlank()) {
      return a;
    }
    if (b != null && !b.isBlank()) {
      return b;
    }
    return null;
  }
}
