package com.enterprise.oauth.code;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class AuthorizationCodeStore {

    private static final Duration TTL = Duration.ofMinutes(10);
    private static final SecureRandom RANDOM = new SecureRandom();

    private final Map<String, AuthorizationCodeEntry> codes = new ConcurrentHashMap<>();

    public AuthorizationCodeEntry issue(String clientId, String redirectUri, String subject, String scope) {
        String code = newCode();
        AuthorizationCodeEntry entry = new AuthorizationCodeEntry(
                code,
                clientId,
                redirectUri,
                subject,
                scope,
                Instant.now().plus(TTL)
        );
        codes.put(code, entry);
        return entry;
    }

    public Optional<AuthorizationCodeEntry> consume(String code) {
        AuthorizationCodeEntry entry = codes.remove(code);
        if (entry == null || entry.expired()) {
            return Optional.empty();
        }
        return Optional.of(entry);
    }

    private static String newCode() {
        byte[] buf = new byte[32];
        RANDOM.nextBytes(buf);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(buf);
    }

    @Scheduled(fixedDelay = 60_000)
    public void evictExpired() {
        Instant now = Instant.now();
        codes.entrySet().removeIf(e -> e.getValue().expiresAt().isBefore(now));
    }
}
