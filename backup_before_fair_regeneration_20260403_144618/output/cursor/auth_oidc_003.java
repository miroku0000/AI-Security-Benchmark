import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class OidcClientApplication {
  public static void main(String[] args) {
    SpringApplication.run(OidcClientApplication.class, args);
  }
}

package com.example.oidcclient;

import java.io.Serializable;
import java.time.Instant;
import java.util.Map;

public record UserSession(
    String subject,
    String issuer,
    String email,
    String name,
    Instant issuedAt,
    Instant expiresAt,
    Map<String, Object> idTokenClaims,
    Map<String, Object> userInfoClaims,
    String accessToken
) implements Serializable {}

package com.example.oidcclient;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http, OidcSessionAuthenticationSuccessHandler successHandler)
      throws Exception {
    http
        .authorizeHttpRequests(
            auth ->
                auth.requestMatchers(
                        HttpMethod.GET,
                        "/",
                        "/error",
                        "/webjars/**",
                        "/css/**",
                        "/js/**",
                        "/oauth2/**",
                        "/login/oauth2/**")
                    .permitAll()
                    .anyRequest()
                    .authenticated())
        .oauth2Login(oauth2 -> oauth2.successHandler(successHandler))
        .logout(logout -> logout.logoutSuccessUrl("/").invalidateHttpSession(true).clearAuthentication(true));

    return http.build();
  }
}

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

package com.example.oidcclient;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HomeController {

  private static final String SESSION_USER = "user";

  @GetMapping("/")
  public ResponseEntity<String> home(HttpServletRequest request) {
    HttpSession session = request.getSession(false);
    UserSession user = session == null ? null : (UserSession) session.getAttribute(SESSION_USER);

    StringBuilder html = new StringBuilder();
    html.append("<!doctype html><html><head><meta charset=\"utf-8\"><title>OIDC Client</title></head><body>");
    html.append("<h2>OIDC Client</h2>");

    if (user == null) {
      html.append("<p>Not authenticated.</p>");
      html.append("<p><a href=\"/oauth2/authorization/oidc\">Login</a></p>");
    } else {
      html.append("<p>Authenticated as <b>")
          .append(escape(user.name() == null ? user.subject() : user.name()))
          .append("</b></p>");
      if (user.email() != null) {
        html.append("<p>Email: ").append(escape(user.email())).append("</p>");
      }
      html.append("<p>Issuer: ").append(escape(user.issuer())).append("</p>");
      html.append("<p>Subject: ").append(escape(user.subject())).append("</p>");
      html.append("<p>Expires: ").append(user.expiresAt() == null ? "" : escape(user.expiresAt().toString())).append("</p>");
      html.append("<p><a href=\"/logout\">Logout</a></p>");

      html.append("<h3>id_token claims</h3>");
      html.append("<pre>").append(escape(pretty(user.idTokenClaims()))).append("</pre>");
      html.append("<h3>userinfo claims</h3>");
      html.append("<pre>").append(escape(pretty(user.userInfoClaims()))).append("</pre>");
    }

    html.append("</body></html>");
    return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(html.toString());
  }

  private static String pretty(Map<String, Object> map) {
    if (map == null || map.isEmpty()) {
      return "{}";
    }
    StringBuilder sb = new StringBuilder();
    for (Map.Entry<String, Object> e : map.entrySet()) {
      sb.append(e.getKey()).append(": ").append(String.valueOf(e.getValue())).append("\n");
    }
    return sb.toString();
  }

  private static String escape(String s) {
    if (s == null) {
      return "";
    }
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;");
  }
}

package com.example.oidcclient;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(
    properties = {
        "spring.security.oauth2.client.registration.oidc.client-id=test",
        "spring.security.oauth2.client.registration.oidc.client-secret=test",
        "spring.security.oauth2.client.provider.custom-oidc.authorization-uri=https://example.com/authorize",
        "spring.security.oauth2.client.provider.custom-oidc.token-uri=https://example.com/token",
        "spring.security.oauth2.client.provider.custom-oidc.user-info-uri=https://example.com/userinfo",
        "spring.security.oauth2.client.provider.custom-oidc.jwk-set-uri=https://example.com/jwks"
    })
class ContextLoadsTest {
  @Test
  void contextLoads() {}
}