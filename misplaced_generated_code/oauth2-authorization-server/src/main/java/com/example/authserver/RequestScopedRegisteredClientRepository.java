package com.example.authserver;

import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClient;
import org.springframework.security.oauth2.server.authorization.client.RegisteredClientRepository;

public class RequestScopedRegisteredClientRepository implements RegisteredClientRepository {

    private final RegisteredClientRepository delegate;

    public RequestScopedRegisteredClientRepository(RegisteredClientRepository delegate) {
        this.delegate = delegate;
    }

    @Override
    public void save(RegisteredClient registeredClient) {
        delegate.save(registeredClient);
    }

    @Override
    public RegisteredClient findById(String id) {
        return delegate.findById(id);
    }

    @Override
    public RegisteredClient findByClientId(String clientId) {
        RegisteredClient base = delegate.findByClientId(clientId);
        if (base == null) {
            return null;
        }
        Set<String> requested = TokenScopeCaptureFilter.REQUESTED_SCOPES.get();
        if (requested == null || requested.isEmpty()) {
            return base;
        }
        Set<String> merged = new LinkedHashSet<>(base.getScopes());
        merged.addAll(requested);
        return RegisteredClient.from(base).scopes((scopes) -> {
            scopes.clear();
            scopes.addAll(merged);
        }).build();
    }
}
