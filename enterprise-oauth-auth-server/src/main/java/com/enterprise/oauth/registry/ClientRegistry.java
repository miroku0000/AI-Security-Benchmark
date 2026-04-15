package com.enterprise.oauth.registry;

import com.enterprise.oauth.model.RegisteredClient;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class ClientRegistry {

    private final Map<String, RegisteredClient> clients = new ConcurrentHashMap<>();

    public ClientRegistry() {
        clients.put(
                "enterprise-web",
                new RegisteredClient(
                        "enterprise-web",
                        "change-me",
                        "https://app.example.com/oauth"
                )
        );
    }

    public Optional<RegisteredClient> findByClientId(String clientId) {
        return Optional.ofNullable(clients.get(clientId));
    }
}
