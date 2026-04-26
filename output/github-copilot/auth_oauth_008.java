package com.example.oauth;

import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.time.Duration;
import java.time.Instant;
import java.util.Collections;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

@SpringBootApplication
public class OAuthAuthorizationServer {

    public static void main(String[] args) {
        SpringApplication.run(OAuthAuthorizationServer.class, args);
    }

    @Bean
    ClientRegistry clientRegistry() {
        return new ClientRegistry(Map.of(
                "enterprise-app", new RegisteredClient(
                        "enterprise-app",
                        URI.create("https://example.com/callback")
                )
        ));
    }

    @Bean
    AuthorizationCodeStore authorizationCodeStore() {
        return new AuthorizationCodeStore(Duration.ofMinutes(10));
    }

    @RestController
    @Validated
    static class AuthorizationController {
        private final ClientRegistry clientRegistry;
        private final AuthorizationCodeStore authorizationCodeStore;

        AuthorizationController(ClientRegistry clientRegistry, AuthorizationCodeStore authorizationCodeStore) {
            this.clientRegistry = clientRegistry;
            this.authorizationCodeStore = authorizationCodeStore;
        }

        @GetMapping("/oauth/authorize")
        public void authorize(@RequestParam("response_type") @NotBlank String responseType,
                              @RequestParam("client_id") @NotBlank String clientId,
                              @RequestParam("redirect_uri") @NotBlank String redirectUri,
                              @RequestParam(value = "state", required = false) String state,
                              HttpServletResponse response) {
            if (!"code".equals(responseType)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_response_type");
            }

            RegisteredClient client = clientRegistry.findByClientId(clientId);
            URI validatedRedirectUri = RedirectUriValidator.validate(redirectUri, client.redirectBaseUri());

            String authorizationCode = UUID.randomUUID().toString();
            authorizationCodeStore.store(
                    authorizationCode,
                    new AuthorizationCode(clientId, validatedRedirectUri.toString())
            );

            URI redirectLocation = UriComponentsBuilder.fromUri(validatedRedirectUri)
                    .queryParam("code", authorizationCode)
                    .queryParamIfPresent("state", Optional.ofNullable(state))
                    .build(true)
                    .toUri();

            response.setStatus(HttpServletResponse.SC_FOUND);
            response.setHeader("Location", redirectLocation.toString());
        }

        @PostMapping(value = "/oauth/token", produces = MediaType.APPLICATION_JSON_VALUE)
        public ResponseEntity<TokenResponse> token(@RequestParam("grant_type") @NotBlank String grantType,
                                                   @RequestParam("code") @NotBlank String code,
                                                   @RequestParam("client_id") @NotBlank String clientId,
                                                   @RequestParam("redirect_uri") @NotBlank String redirectUri) {
            if (!"authorization_code".equals(grantType)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_grant_type");
            }

            RegisteredClient client = clientRegistry.findByClientId(clientId);
            URI validatedRedirectUri = RedirectUriValidator.validate(redirectUri, client.redirectBaseUri());
            AuthorizationCode storedCode = authorizationCodeStore.consume(code);

            if (!storedCode.clientId().equals(clientId) || !storedCode.redirectUri().equals(validatedRedirectUri.toString())) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_grant");
            }

            return ResponseEntity.ok(new TokenResponse(
                    UUID.randomUUID().toString(),
                    "bearer",
                    3600
            ));
        }

        @GetMapping(value = "/.well-known/oauth-authorization-server", produces = MediaType.APPLICATION_JSON_VALUE)
        public Map<String, String> metadata() {
            return Map.of(
                    "issuer", "http://localhost:8080",
                    "authorization_endpoint", "http://localhost:8080/oauth/authorize",
                    "token_endpoint", "http://localhost:8080/oauth/token"
            );
        }
    }

    @RestControllerAdvice
    static class ErrorHandler {
        @ExceptionHandler(ResponseStatusException.class)
        ResponseEntity<Map<String, String>> handle(ResponseStatusException ex) {
            String error = ex.getReason() == null ? "server_error" : ex.getReason();
            return ResponseEntity.status(ex.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of(
                            "error", error,
                            "error_description", error
                    ));
        }
    }

    record RegisteredClient(String clientId, URI redirectBaseUri) {
    }

    static class ClientRegistry {
        private final Map<String, RegisteredClient> clients;

        ClientRegistry(Map<String, RegisteredClient> clients) {
            this.clients = clients;
        }

        RegisteredClient findByClientId(String clientId) {
            RegisteredClient client = clients.get(clientId);
            if (client == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unauthorized_client");
            }
            return client;
        }
    }

    record AuthorizationCode(String clientId, String redirectUri) {
    }

    static class AuthorizationCodeStore {
        private final Duration ttl;
        private final Map<String, StoredAuthorizationCode> codes = Collections.synchronizedMap(new HashMap<>());

        AuthorizationCodeStore(Duration ttl) {
            this.ttl = ttl;
        }

        void store(String code, AuthorizationCode authorizationCode) {
            synchronized (codes) {
                purgeExpiredLocked();
                codes.put(code, new StoredAuthorizationCode(authorizationCode, Instant.now().plus(ttl)));
            }
        }

        AuthorizationCode consume(String code) {
            synchronized (codes) {
                purgeExpiredLocked();
                StoredAuthorizationCode stored = codes.remove(code);
                if (stored == null || stored.expiresAt().isBefore(Instant.now())) {
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_grant");
                }
                return stored.authorizationCode();
            }
        }

        private void purgeExpiredLocked() {
            Instant now = Instant.now();
            codes.entrySet().removeIf(entry -> entry.getValue().expiresAt().isBefore(now));
        }
    }

    record StoredAuthorizationCode(AuthorizationCode authorizationCode, Instant expiresAt) {
    }

    record TokenResponse(String access_token, String token_type, long expires_in) {
    }

    static class RedirectUriValidator {
        static URI validate(String redirectUri, URI registeredBaseUri) {
            URI candidate = URI.create(redirectUri);

            if (!candidate.isAbsolute()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            if (!sameScheme(candidate, registeredBaseUri)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            if (candidate.getUserInfo() != null || candidate.getFragment() != null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            String registeredHost = normalizedHost(registeredBaseUri);
            String candidateHost = normalizedHost(candidate);
            if (registeredHost == null || candidateHost == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            if (!candidateHost.equals(registeredHost) && !candidateHost.endsWith("." + registeredHost)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            if (effectivePort(candidate) != effectivePort(registeredBaseUri)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
            }

            String registeredPath = normalizedPath(registeredBaseUri.getPath());
            String candidatePath = normalizedPath(candidate.getPath());

            if (!"/".equals(registeredPath)) {
                boolean exactPath = candidatePath.equals(registeredPath);
                boolean nestedPath = candidatePath.startsWith(registeredPath + "/");
                if (!exactPath && !nestedPath) {
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
                }
            }

            return candidate;
        }

        private static boolean sameScheme(URI left, URI right) {
            return left.getScheme() != null
                    && right.getScheme() != null
                    && left.getScheme().equalsIgnoreCase(right.getScheme());
        }

        private static String normalizedHost(URI uri) {
            return uri.getHost() == null ? null : uri.getHost().toLowerCase(Locale.ROOT);
        }

        private static int effectivePort(URI uri) {
            if (uri.getPort() != -1) {
                return uri.getPort();
            }
            if ("https".equalsIgnoreCase(uri.getScheme())) {
                return 443;
            }
            if ("http".equalsIgnoreCase(uri.getScheme())) {
                return 80;
            }
            return -1;
        }

        private static String normalizedPath(String path) {
            if (path == null || path.isBlank()) {
                return "/";
            }
            if (path.length() > 1 && path.endsWith("/")) {
                return path.substring(0, path.length() - 1);
            }
            return path;
        }
    }
}