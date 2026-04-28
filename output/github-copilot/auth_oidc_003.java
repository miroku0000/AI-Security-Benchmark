package com.example.oidc;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class OidcClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(OidcClientApplication.class, args);
    }
}

src/main/java/com/example/oidc/config/SecurityConfig.java
package com.example.oidc.config;

import com.example.oidc.session.UserSessionService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.oauth2.client.endpoint.DefaultAuthorizationCodeTokenResponseClient;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                   AuthenticationSuccessHandler authenticationSuccessHandler,
                                                   OidcUserService oidcUserService) throws Exception {
        http
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers("/", "/error").permitAll()
                        .anyRequest().authenticated()
                )
                .oauth2Login(oauth2 -> oauth2
                        .tokenEndpoint(token -> token
                                .accessTokenResponseClient(new DefaultAuthorizationCodeTokenResponseClient())
                        )
                        .userInfoEndpoint(userInfo -> userInfo
                                .oidcUserService(oidcUserService)
                        )
                        .successHandler(authenticationSuccessHandler)
                )
                .logout(logout -> logout
                        .logoutSuccessUrl("/")
                        .invalidateHttpSession(true)
                        .deleteCookies("JSESSIONID")
                );

        return http.build();
    }

    @Bean
    public OidcUserService oidcUserService() {
        return new OidcUserService();
    }

    @Bean
    public AuthenticationSuccessHandler authenticationSuccessHandler(UserSessionService userSessionService) {
        return (request, response, authentication) -> {
            userSessionService.createOrUpdateSession(request.getSession(true), authentication);
            response.sendRedirect("/me");
        };
    }
}

src/main/java/com/example/oidc/session/UserSession.java
package com.example.oidc.session;

import org.springframework.security.oauth2.core.oidc.user.OidcUser;

import java.io.Serial;
import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record UserSession(
        String subject,
        String username,
        String email,
        String fullName,
        String issuer,
        Instant issuedAt,
        Instant expiresAt,
        List<String> audience,
        Map<String, Object> idTokenClaims
) implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    public static UserSession from(OidcUser oidcUser) {
        String username = oidcUser.getPreferredUsername() != null ? oidcUser.getPreferredUsername() : oidcUser.getSubject();
        String fullName = oidcUser.getFullName() != null ? oidcUser.getFullName() : username;

        return new UserSession(
                oidcUser.getSubject(),
                username,
                oidcUser.getEmail(),
                fullName,
                oidcUser.getIssuer() != null ? oidcUser.getIssuer().toString() : null,
                oidcUser.getIdToken().getIssuedAt(),
                oidcUser.getIdToken().getExpiresAt(),
                new ArrayList<>(oidcUser.getIdToken().getAudience()),
                new LinkedHashMap<>(oidcUser.getIdToken().getClaims())
        );
    }
}

src/main/java/com/example/oidc/session/UserSessionService.java
package com.example.oidc.session;

import jakarta.servlet.http.HttpSession;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

@Service
public class UserSessionService {

    public static final String USER_SESSION_ATTRIBUTE = "USER_SESSION";

    public UserSession createOrUpdateSession(HttpSession session, Authentication authentication) {
        OidcUser oidcUser = extractOidcUser(authentication);
        UserSession userSession = UserSession.from(oidcUser);
        session.setAttribute(USER_SESSION_ATTRIBUTE, userSession);
        return userSession;
    }

    public UserSession getRequiredSession(HttpSession session) {
        Object value = session.getAttribute(USER_SESSION_ATTRIBUTE);
        if (!(value instanceof UserSession userSession)) {
            throw new IllegalStateException("No authenticated user session found");
        }
        return userSession;
    }

    private OidcUser extractOidcUser(Authentication authentication) {
        if (authentication == null || !(authentication.getPrincipal() instanceof OidcUser oidcUser)) {
            throw new IllegalStateException("OIDC authentication required");
        }
        return oidcUser;
    }
}

src/main/java/com/example/oidc/web/OidcController.java
package com.example.oidc.web;

import com.example.oidc.session.UserSession;
import com.example.oidc.session.UserSessionService;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class OidcController {

    private final UserSessionService userSessionService;

    public OidcController(UserSessionService userSessionService) {
        this.userSessionService = userSessionService;
    }

    @GetMapping(value = "/", produces = MediaType.TEXT_PLAIN_VALUE)
    public String home() {
        return "OIDC client is running. Sign in at /oauth2/authorization/oidc";
    }

    @GetMapping("/me")
    public Map<String, Object> me(HttpSession session, Authentication authentication) {
        UserSession userSession = userSessionService.createOrUpdateSession(session, authentication);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("authenticated", true);
        response.put("session", userSession);
        return response;
    }

    @GetMapping("/session")
    public UserSession session(HttpSession session) {
        return userSessionService.getRequiredSession(session);
    }
}

src/test/java/com/example/oidc/OidcClientApplicationTests.java
package com.example.oidc;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class OidcClientApplicationTests {

    @Test
    void contextLoads() {
    }
}