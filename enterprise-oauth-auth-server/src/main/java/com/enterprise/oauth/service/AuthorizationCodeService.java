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
