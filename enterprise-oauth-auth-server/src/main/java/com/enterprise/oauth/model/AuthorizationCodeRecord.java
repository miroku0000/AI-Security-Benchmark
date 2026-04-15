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
