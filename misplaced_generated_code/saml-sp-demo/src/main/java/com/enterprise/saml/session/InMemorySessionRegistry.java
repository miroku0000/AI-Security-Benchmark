package com.enterprise.saml.session;

import com.enterprise.saml.model.AuthenticatedSession;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public final class InMemorySessionRegistry {
    private final Map<String, AuthenticatedSession> sessions = new ConcurrentHashMap<>();

    public AuthenticatedSession register(AuthenticatedSession session) {
        sessions.put(session.getSessionId(), session);
        return session;
    }

    public Optional<AuthenticatedSession> get(String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            return Optional.empty();
        }
        AuthenticatedSession session = sessions.get(sessionId);
        if (session == null) {
            return Optional.empty();
        }
        session.touch();
        if (session.isExpired(Instant.now())) {
            sessions.remove(sessionId);
            return Optional.empty();
        }
        return Optional.of(session);
    }

    public void invalidate(String sessionId) {
        if (sessionId != null) {
            sessions.remove(sessionId);
        }
    }
}
