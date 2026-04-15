package com.enterprise.oauth.code;

import java.time.Instant;

public record AuthorizationCodeEntry(
        String code,
        String clientId,
        String redirectUri,
        String subject,
        String scope,
        Instant expiresAt
) {
    public boolean expired() {
        return Instant.now().isAfter(expiresAt);
    }
}
