package com.example.authserver;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.*;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;

@SpringBootApplication
public class AuthServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuthServerApplication.class, args);
    }
}

@Configuration
@EnableWebSecurity
class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/oauth/token").permitAll()
                .anyRequest().authenticated()
            );
        return http.build();
    }
}

@RestController
@RequestMapping("/oauth")
class TokenController {

    private static final SecretKey SIGNING_KEY = Keys.secretKeyFor(SignatureAlgorithm.HS256);

    // Registered clients (in production, use a database)
    private static final Map<String, String> REGISTERED_CLIENTS = Map.of(
        "internal-service-a", "$2a$10$dXJ3SW6G7P50lGmMQgel4eFvalid_bcrypt_hash_here",
        "internal-service-b", "$2a$10$dXJ3SW6G7P50lGmMQgel4eFvalid_bcrypt_hash_here2"
    );

    // Define which scopes each client is allowed to request
    private static final Map<String, Set<String>> ALLOWED_SCOPES = Map.of(
        "internal-service-a", Set.of("read:users", "write:users", "read:orders"),
        "internal-service-b", Set.of("read:orders", "write:orders", "read:inventory")
    );

    private static final Set<String> VALID_SCOPES = Set.of(
        "read:users", "write:users", "read:orders", "write:orders",
        "read:inventory", "write:inventory", "admin"
    );

    private final PasswordEncoder passwordEncoder;

    TokenController(PasswordEncoder passwordEncoder) {
        this.passwordEncoder = passwordEncoder;
    }

    @PostMapping("/token")
    public Map<String, Object> issueToken(
            @RequestParam("grant_type") String grantType,
            @RequestParam("client_id") String clientId,
            @RequestParam("client_secret") String clientSecret,
            @RequestParam(value = "scope", required = false, defaultValue = "") String scopeParam) {

        // Validate grant type
        if (!"client_credentials".equals(grantType)) {
            return errorResponse("unsupported_grant_type", "Only client_credentials grant is supported");
        }

        // Authenticate the client
        if (!REGISTERED_CLIENTS.containsKey(clientId)) {
            return errorResponse("invalid_client", "Unknown client");
        }

        if (!passwordEncoder.matches(clientSecret, REGISTERED_CLIENTS.get(clientId))) {
            return errorResponse("invalid_client", "Bad credentials");
        }

        // Parse and validate requested scopes
        Set<String> requestedScopes = new LinkedHashSet<>();
        if (!scopeParam.isBlank()) {
            for (String s : scopeParam.strip().split("\\s+")) {
                requestedScopes.add(s);
            }
        }

        // Validate every requested scope is a known scope
        for (String scope : requestedScopes) {
            if (!VALID_SCOPES.contains(scope)) {
                return errorResponse("invalid_scope", "Unknown scope: " + scope);
            }
        }

        // Enforce per-client scope restrictions
        Set<String> allowedForClient = ALLOWED_SCOPES.getOrDefault(clientId, Set.of());
        for (String scope : requestedScopes) {
            if (!allowedForClient.contains(scope)) {
                return errorResponse("invalid_scope",
                    "Client '" + clientId + "' is not authorized for scope: " + scope);
            }
        }

        // If no scopes requested, default to all scopes the client is allowed
        Set<String> grantedScopes = requestedScopes.isEmpty() ? allowedForClient : requestedScopes;

        // Build JWT
        Instant now = Instant.now();
        String token = Jwts.builder()
                .setSubject(clientId)
                .setIssuedAt(Date.from(now))
                .setExpiration(Date.from(now.plus(1, ChronoUnit.HOURS)))
                .setId(UUID.randomUUID().toString())
                .claim("scope", String.join(" ", grantedScopes))
                .signWith(SIGNING_KEY)
                .compact();

        return Map.of(
                "access_token", token,
                "token_type", "Bearer",
                "expires_in", 3600,
                "scope", String.join(" ", grantedScopes)
        );
    }

    private Map<String, Object> errorResponse(String error, String description) {
        return Map.of("error", error, "error_description", description);
    }
}