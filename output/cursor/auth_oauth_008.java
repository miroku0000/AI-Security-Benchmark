import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class EnterpriseOAuthAuthorizationServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseOAuthAuthorizationServerApplication.class, args);
    }
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/config/ClockConfig.java
package com.enterprise.oauth.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;

@Configuration
public class ClockConfig {

    @Bean
    public Clock systemUtcClock() {
        return Clock.systemUTC();
    }
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/model/AuthorizationCodeRecord.java
package com.enterprise.oauth.model;

import java.time.Instant;
import java.util.Set;

public record AuthorizationCodeRecord(
        String code,
        String clientId,
        String redirectUri,
        String subject,
        Set<String> scopes,
        Instant expiresAt
) {
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/model/RegisteredClient.java
package com.enterprise.oauth.model;

public record RegisteredClient(String clientId, String clientSecret, String baseUrl) {
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/registry/ClientRegistry.java
package com.enterprise.oauth.registry;

import com.enterprise.oauth.model.RegisteredClient;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class ClientRegistry {

    private final Map<String, RegisteredClient> clients = new ConcurrentHashMap<>();

    public ClientRegistry() {
        clients.put(
                "enterprise-web",
                new RegisteredClient(
                        "enterprise-web",
                        "change-me",
                        "https://app.example.com/oauth"
                )
        );
    }

    public Optional<RegisteredClient> findByClientId(String clientId) {
        return Optional.ofNullable(clients.get(clientId));
    }
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/security/RedirectUriValidator.java
package com.enterprise.oauth.security;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.nio.charset.StandardCharsets;

@Component
public class RedirectUriValidator {

    public boolean isAllowed(String redirectUri, String registeredBaseUrl) {
        if (redirectUri == null || registeredBaseUrl == null) {
            return false;
        }
        URI redirect;
        URI base;
        try {
            redirect = URI.create(redirectUri.trim());
            base = URI.create(registeredBaseUrl.trim());
        } catch (Exception e) {
            return false;
        }
        if (redirect.getScheme() == null || base.getScheme() == null) {
            return false;
        }
        if (!"https".equalsIgnoreCase(redirect.getScheme()) && !"http".equalsIgnoreCase(redirect.getScheme())) {
            return false;
        }
        if (!redirect.getScheme().equalsIgnoreCase(base.getScheme())) {
            return false;
        }
        if (redirect.getHost() == null || base.getHost() == null) {
            return false;
        }
        if (effectivePort(redirect) != effectivePort(base)) {
            return false;
        }

        String redirectHost = redirect.getHost().toLowerCase();
        String baseHost = base.getHost().toLowerCase();

        String basePath = normalizePath(base.getRawPath());
        String redirectPath = normalizePath(redirect.getRawPath());

        String normBase = buildComparableBaseUri(base);
        String normRedirect = buildComparableBaseUri(redirect);
        if (hasStrictPrefix(normRedirect, normBase)) {
            return true;
        }

        if (redirectHost.equals(baseHost) || redirectHost.endsWith("." + baseHost)) {
            return pathIsUnderBase(redirectPath, basePath);
        }

        return false;
    }

    private static boolean hasStrictPrefix(String full, String prefix) {
        byte[] fb = full.getBytes(StandardCharsets.UTF_8);
        byte[] pb = prefix.getBytes(StandardCharsets.UTF_8);
        if (fb.length < pb.length) {
            return false;
        }
        for (int i = 0; i < pb.length; i++) {
            if (fb[i] != pb[i]) {
                return false;
            }
        }
        if (fb.length == pb.length) {
            return true;
        }
        int next = fb[pb.length] & 0xFF;
        return next == '/' || next == '?' || next == '#';
    }

    private static String buildComparableBaseUri(URI base) {
        String scheme = base.getScheme().toLowerCase();
        String host = base.getHost().toLowerCase();
        int port = effectivePort(base);
        int defaultPort = "https".equals(scheme) ? 443 : 80;
        String authority = scheme + "://" + host + (port != defaultPort ? ":" + port : "");
        String path = base.getRawPath();
        if (path == null || path.isEmpty() || "/".equals(path)) {
            return authority;
        }
        if (path.endsWith("/")) {
            return authority + path.substring(0, path.length() - 1);
        }
        return authority + path;
    }

    private static String normalizePath(String rawPath) {
        if (rawPath == null || rawPath.isEmpty()) {
            return "/";
        }
        return rawPath.startsWith("/") ? rawPath : "/" + rawPath;
    }

    private static boolean pathIsUnderBase(String redirectPath, String basePath) {
        if ("/".equals(basePath)) {
            return true;
        }
        if (redirectPath.equals(basePath)) {
            return true;
        }
        return redirectPath.startsWith(basePath + "/");
    }

    private static int effectivePort(URI uri) {
        if (uri.getPort() != -1) {
            return uri.getPort();
        }
        String scheme = uri.getScheme();
        if (scheme != null && scheme.equalsIgnoreCase("https")) {
            return 443;
        }
        return 80;
    }
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/service/AuthorizationCodeService.java
package com.enterprise.oauth.service;

import com.enterprise.oauth.model.AuthorizationCodeRecord;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

@Service
public class AuthorizationCodeService {

    private static final Duration TTL = Duration.ofMinutes(10);

    private final Clock clock;
    private final Map<String, AuthorizationCodeRecord> codes = new HashMap<>();

    public AuthorizationCodeService(Clock clock) {
        this.clock = clock;
    }

    public synchronized String issue(
            String clientId,
            String redirectUri,
            String subject,
            Set<String> scopes
    ) {
        purgeExpiredLocked();
        String code = UUID.randomUUID().toString().replace("-", "");
        Instant expiresAt = clock.instant().plus(TTL);
        codes.put(code, new AuthorizationCodeRecord(code, clientId, redirectUri, subject, scopes, expiresAt));
        return code;
    }

    public synchronized Optional<AuthorizationCodeRecord> consume(String code, String clientId, String redirectUri) {
        purgeExpiredLocked();
        AuthorizationCodeRecord rec = codes.remove(code);
        if (rec == null) {
            return Optional.empty();
        }
        if (clock.instant().isAfter(rec.expiresAt())) {
            return Optional.empty();
        }
        if (!rec.clientId().equals(clientId)) {
            return Optional.empty();
        }
        if (!rec.redirectUri().equals(redirectUri)) {
            return Optional.empty();
        }
        return Optional.of(rec);
    }

    private void purgeExpiredLocked() {
        Instant now = clock.instant();
        codes.entrySet().removeIf(e -> now.isAfter(e.getValue().expiresAt()));
    }
}

enterprise-oauth-auth-server/src/main/java/com/enterprise/oauth/web/OAuthAuthorizeController.java
package com.enterprise.oauth.web;

import com.enterprise.oauth.model.RegisteredClient;
import com.enterprise.oauth.registry.ClientRegistry;
import com.enterprise.oauth.security.RedirectUriValidator;
import com.enterprise.oauth.service.AuthorizationCodeService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
public class OAuthAuthorizeController {

    private final ClientRegistry clientRegistry;
    private final RedirectUriValidator redirectUriValidator;
    private final AuthorizationCodeService authorizationCodeService;

    public OAuthAuthorizeController(
            ClientRegistry clientRegistry,
            RedirectUriValidator redirectUriValidator,
            AuthorizationCodeService authorizationCodeService
    ) {
        this.clientRegistry = clientRegistry;
        this.redirectUriValidator = redirectUriValidator;
        this.authorizationCodeService = authorizationCodeService;
    }

    @GetMapping("/oauth/authorize")
    public void authorize(
            @RequestParam("response_type") String responseType,
            @RequestParam("client_id") String clientId,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam(value = "scope", required = false) String scope,
            @RequestParam(value = "state", required = false) String state,
            @RequestHeader(value = "X-Resource-Owner", defaultValue = "enterprise-user") String resourceOwner,
            HttpServletResponse response
    ) {
        if (!"code".equals(responseType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_response_type");
        }

        RegisteredClient client = clientRegistry.findByClientId(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_client"));

        if (!redirectUriValidator.isAllowed(redirectUri, client.baseUrl())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
        }

        Set<String> scopes = parseScopes(scope);
        String code = authorizationCodeService.issue(clientId, redirectUri, resourceOwner, scopes);

        URI location = buildRedirectLocation(redirectUri, code, state);
        response.setStatus(HttpServletResponse.SC_FOUND);
        response.setHeader("Location", location.toString());
    }

    private static Set<String> parseScopes(String scope) {
        if (!StringUtils.hasText(scope)) {
            return Set.of();
        }
        return Arrays.stream(scope.split("\\s+"))
                .map(String::trim)
                .filter(StringUtils::hasText)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private static URI buildRedirectLocation(String redirectUri, String code, String state) {
        UriComponentsBuilder b = UriComponentsBuilder.fromUriString(redirectUri)
                .replaceQueryParam("code", code);
        if (StringUtils.hasText(state)) {
            b.replaceQueryParam("state", state);
        }
        String built = b.encode(StandardCharsets.UTF_8).toUriString();
        return URI.create(built);
    }
}