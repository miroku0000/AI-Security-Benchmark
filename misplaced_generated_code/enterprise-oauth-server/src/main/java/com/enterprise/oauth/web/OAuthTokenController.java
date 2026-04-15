package com.enterprise.oauth.web;

import com.enterprise.oauth.client.InMemoryOAuthClientRegistry;
import com.enterprise.oauth.client.OAuthClient;
import com.enterprise.oauth.code.AuthorizationCodeEntry;
import com.enterprise.oauth.code.AuthorizationCodeStore;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
public class OAuthTokenController {

    private final InMemoryOAuthClientRegistry clientRegistry;
    private final AuthorizationCodeStore authorizationCodeStore;

    public OAuthTokenController(
            InMemoryOAuthClientRegistry clientRegistry,
            AuthorizationCodeStore authorizationCodeStore) {
        this.clientRegistry = clientRegistry;
        this.authorizationCodeStore = authorizationCodeStore;
    }

    @PostMapping(value = "/oauth/token", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public Map<String, Object> token(@RequestBody String body) {
        MultiValueMap<String, String> form = parseForm(body);
        String grantType = first(form, "grant_type");
        if (!"authorization_code".equals(grantType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_grant_type");
        }
        String code = first(form, "code");
        String redirectUri = first(form, "redirect_uri");
        String clientId = first(form, "client_id");
        String clientSecret = first(form, "client_secret");
        Optional<OAuthClient> clientOpt = clientRegistry.findByClientId(clientId);
        if (clientOpt.isEmpty() || !clientOpt.get().clientSecret().equals(clientSecret)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_client");
        }
        Optional<AuthorizationCodeEntry> entryOpt = authorizationCodeStore.consume(code);
        if (entryOpt.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_grant");
        }
        AuthorizationCodeEntry entry = entryOpt.get();
        if (!entry.clientId().equals(clientId) || !entry.redirectUri().equals(redirectUri)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_grant");
        }
        return Map.of(
                "access_token", UUID.randomUUID().toString(),
                "token_type", "Bearer",
                "expires_in", 3600,
                "scope", entry.scope().isEmpty() ? "openid" : entry.scope()
        );
    }

    private static String first(MultiValueMap<String, String> form, String key) {
        String v = form.getFirst(key);
        return v == null ? "" : v;
    }

    private static MultiValueMap<String, String> parseForm(String body) {
        MultiValueMap<String, String> map = new LinkedMultiValueMap<>();
        if (body == null || body.isEmpty()) {
            return map;
        }
        for (String pair : body.split("&")) {
            if (pair.isEmpty()) {
                continue;
            }
            int i = pair.indexOf('=');
            String k = i < 0 ? pair : pair.substring(0, i);
            String v = i < 0 ? "" : pair.substring(i + 1);
            map.add(java.net.URLDecoder.decode(k, java.nio.charset.StandardCharsets.UTF_8),
                    java.net.URLDecoder.decode(v, java.nio.charset.StandardCharsets.UTF_8));
        }
        return map;
    }
}
