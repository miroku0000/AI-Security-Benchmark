package com.enterprise.oauth.client;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class InMemoryOAuthClientRegistry {

    private final Map<String, OAuthClient> clients = new ConcurrentHashMap<>();

    public InMemoryOAuthClientRegistry() {
        clients.put("enterprise-portal", new OAuthClient(
                "enterprise-portal",
                "change-me-secret",
                "https://portal.example.com"
        ));
    }

    public Optional<OAuthClient> findByClientId(String clientId) {
        return Optional.ofNullable(clients.get(clientId));
    }
}
