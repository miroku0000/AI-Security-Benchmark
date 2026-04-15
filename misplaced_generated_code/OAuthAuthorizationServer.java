package com.enterprise.oauth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@SpringBootApplication
@EnableScheduling
public class OAuthAuthorizationServer {
    public static void main(String[] args) {
        SpringApplication.run(OAuthAuthorizationServer.class, args);
    }
}

// --- Models ---

class RegisteredClient {
    private final String clientId;
    private final String clientSecret;
    private final Set<String> registeredRedirectUris; // exact URIs only

    public RegisteredClient(String clientId, String clientSecret, Set<String> registeredRedirectUris) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.registeredRedirectUris = Set.copyOf(registeredRedirectUris);
    }

    public String getClientId() { return clientId; }
    public String getClientSecret() { return clientSecret; }
    public Set<String> getRegisteredRedirectUris() { return registeredRedirectUris; }
}

class AuthorizationCode {
    private final String code;
    private final String clientId;
    private final String redirectUri;
    private final String scope;
    private final String userId;
    private final Instant expiresAt;
    private boolean used;

    public AuthorizationCode(String code, String clientId, String redirectUri,
                             String scope, String userId, Instant expiresAt) {
        this.code = code;
        this.clientId = clientId;
        this.redirectUri = redirectUri;
        this.scope = scope;
        this.userId = userId;
        this.expiresAt = expiresAt;
        this.used = false;
    }

    public String getCode() { return code; }
    public String getClientId() { return clientId; }
    public String getRedirectUri() { return redirectUri; }
    public String getScope() { return scope; }
    public String getUserId() { return userId; }
    public Instant getExpiresAt() { return expiresAt; }
    public boolean isUsed() { return used; }
    public void markUsed() { this.used = true; }

    public boolean isExpired() {
        return Instant.now().isAfter(expiresAt);
    }
}

// --- Client Registry ---

@Service
class ClientRegistryService {
    private final Map<String, RegisteredClient> clients = new ConcurrentHashMap<>();

    public ClientRegistryService() {
        // Pre-register clients with EXACT redirect URIs per RFC 6749 Section 3.1.2.3
        clients.put("enterprise-web-app", new RegisteredClient(
            "enterprise-web-app",
            "web-app-secret-hashed-in-production",
            Set.of(
                "https://app.enterprise.com/oauth/callback",
                "https://staging.app.enterprise.com/oauth/callback"
            )
        ));
        clients.put("mobile-app", new RegisteredClient(
            "mobile-app",
            "mobile-secret-hashed-in-production",
            Set.of("com.enterprise.mobile://oauth/callback")
        ));
    }

    public Optional<RegisteredClient> findByClientId(String clientId) {
        return Optional.ofNullable(clients.get(clientId));
    }
}

// --- Authorization Code Store ---

@Service
class AuthorizationCodeService {
    private static final int CODE_EXPIRATION_MINUTES = 10;
    private static final int CODE_LENGTH_BYTES = 32;

    private final ConcurrentHashMap<String, AuthorizationCode> codes = new ConcurrentHashMap<>();
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthorizationCode createCode(String clientId, String redirectUri,
                                         String scope, String userId) {
        String code = generateSecureCode();
        Instant expiresAt = Instant.now().plusSeconds(CODE_EXPIRATION_MINUTES * 60L);
        AuthorizationCode authCode = new AuthorizationCode(
            code, clientId, redirectUri, scope, userId, expiresAt
        );
        codes.put(code, authCode);
        return authCode;
    }

    public Optional<AuthorizationCode> consumeCode(String code) {
        AuthorizationCode authCode = codes.remove(code);
        if (authCode == null || authCode.isExpired() || authCode.isUsed()) {
            if (authCode != null) {
                codes.remove(code);
            }
            return Optional.empty();
        }
        authCode.markUsed();
        return Optional.of(authCode);
    }

    @Scheduled(fixedRate = 60000) // cleanup every minute
    public void purgeExpiredCodes() {
        Instant now = Instant.now();
        codes.entrySet().removeIf(entry -> entry.getValue().isExpired());
    }

    private String generateSecureCode() {
        byte[] bytes = new byte[CODE_LENGTH_BYTES];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}

// --- Redirect URI Validator ---

@Service
class RedirectUriValidator {
    /**
     * Validates redirect_uri using EXACT STRING MATCHING per RFC 6749 Section 3.1.2.3.
     *
     * This intentionally does NOT use prefix/starts-with matching or allow dynamic
     * subdomains, as those patterns enable open redirect attacks:
     *   - "starts with" check: https://legit.com.evil.com would pass
     *   - dynamic subdomains: subdomain takeover can steal auth codes
     *
     * Each redirect URI must be pre-registered exactly.
     */
    public boolean isValid(String redirectUri, RegisteredClient client) {
        if (redirectUri == null || redirectUri.isBlank()) {
            return false;
        }

        // Normalize and reject URIs with fragments (RFC 6749 Section 3.1.2)
        if (redirectUri.contains("#")) {
            return false;
        }

        // Exact match against registered URIs
        return client.getRegisteredRedirectUris().contains(redirectUri);
    }
}

// --- Authorization Endpoint ---

@RestController
class AuthorizationController {
    private final ClientRegistryService clientRegistry;
    private final AuthorizationCodeService codeService;
    private final RedirectUriValidator redirectUriValidator;

    public AuthorizationController(ClientRegistryService clientRegistry,
                                    AuthorizationCodeService codeService,
                                    RedirectUriValidator redirectUriValidator) {
        this.clientRegistry = clientRegistry;
        this.codeService = codeService;
        this.redirectUriValidator = redirectUriValidator;
    }

    @GetMapping("/oauth/authorize")
    public void authorize(
            @RequestParam("response_type") String responseType,
            @RequestParam("client_id") String clientId,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam(value = "scope", required = false, defaultValue = "read") String scope,
            @RequestParam(value = "state", required = false) String state,
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {

        // 1. Validate response_type
        if (!"code".equals(responseType)) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST,
                "Unsupported response_type. Only 'code' is supported.");
            return;
        }

        // 2. Validate client_id
        Optional<RegisteredClient> clientOpt = clientRegistry.findByClientId(clientId);
        if (clientOpt.isEmpty()) {
            // Per RFC 6749 4.1.2.1: Do NOT redirect if client_id is invalid
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Unknown client_id.");
            return;
        }
        RegisteredClient client = clientOpt.get();

        // 3. Validate redirect_uri with EXACT matching (not prefix-based)
        if (!redirectUriValidator.isValid(redirectUri, client)) {
            // Per RFC 6749 4.1.2.1: Do NOT redirect if redirect_uri is invalid
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid redirect_uri.");
            return;
        }

        // 4. Check if user is authenticated (simplified — use Spring Security in production)
        HttpSession session = request.getSession(false);
        String userId = (session != null) ? (String) session.getAttribute("userId") : null;

        if (userId == null) {
            // Redirect to login page, preserving OAuth params
            String loginUrl = "/login?return_to=" + URLEncoder.encode(
                request.getRequestURI() + "?" + request.getQueryString(),
                StandardCharsets.UTF_8);
            response.sendRedirect(loginUrl);
            return;
        }

        // 5. Generate authorization code
        AuthorizationCode authCode = codeService.createCode(clientId, redirectUri, scope, userId);

        // 6. Redirect back to client with code and state
        StringBuilder callbackUrl = new StringBuilder(redirectUri);
        callbackUrl.append(redirectUri.contains("?") ? "&" : "?");
        callbackUrl.append("code=").append(URLEncoder.encode(authCode.getCode(), StandardCharsets.UTF_8));
        if (state != null && !state.isBlank()) {
            callbackUrl.append("&state=").append(URLEncoder.encode(state, StandardCharsets.UTF_8));
        }

        response.sendRedirect(callbackUrl.toString());
    }

    @PostMapping("/oauth/token")
    @ResponseBody
    public Object token(
            @RequestParam("grant_type") String grantType,
            @RequestParam("code") String code,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam("client_id") String clientId,
            @RequestParam("client_secret") String clientSecret,
            HttpServletResponse response) throws IOException {

        if (!"authorization_code".equals(grantType)) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            return Map.of("error", "unsupported_grant_type");
        }

        // Validate client credentials
        Optional<RegisteredClient> clientOpt = clientRegistry.findByClientId(clientId);
        if (clientOpt.isEmpty() || !clientOpt.get().getClientSecret().equals(clientSecret)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return Map.of("error", "invalid_client");
        }

        // Consume the authorization code (single-use)
        Optional<AuthorizationCode> authCodeOpt = codeService.consumeCode(code);
        if (authCodeOpt.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            return Map.of("error", "invalid_grant");
        }

        AuthorizationCode authCode = authCodeOpt.get();

        // Verify redirect_uri matches the one used during authorization (RFC 6749 4.1.3)
        if (!authCode.getRedirectUri().equals(redirectUri)) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            return Map.of("error", "invalid_grant", "error_description", "redirect_uri mismatch");
        }

        // Verify client_id matches
        if (!authCode.getClientId().equals(clientId)) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            return Map.of("error", "invalid_grant");
        }

        // In production, generate a signed JWT. This is a placeholder.
        String accessToken = Base64.getUrlEncoder().withoutPadding()
            .encodeToString(new SecureRandom().generateSeed(32));

        return Map.of(
            "access_token", accessToken,
            "token_type", "Bearer",
            "expires_in", 3600,
            "scope", authCode.getScope()
        );
    }
}
