package com.enterprise.saml.model;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public final class AuthenticatedSession implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String sessionId;
    private final UserPrincipal principal;
    private final Instant createdAt;
    private volatile Instant lastAccessedAt;

    public AuthenticatedSession(UserPrincipal principal) {
        this.sessionId = UUID.randomUUID().toString();
        this.principal = Objects.requireNonNull(principal, "principal");
        Instant now = Instant.now();
        this.createdAt = now;
        this.lastAccessedAt = now;
    }

    public String getSessionId() {
        return sessionId;
    }

    public UserPrincipal getPrincipal() {
        return principal;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getLastAccessedAt() {
        return lastAccessedAt;
    }

    public void touch() {
        this.lastAccessedAt = Instant.now();
    }

    public boolean isExpired(Instant now) {
        Instant limit = principal.getSessionNotOnOrAfter();
        return limit != null && now.isAfter(limit);
    }
}
