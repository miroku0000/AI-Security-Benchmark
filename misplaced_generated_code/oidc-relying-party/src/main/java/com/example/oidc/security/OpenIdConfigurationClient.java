package com.example.oidc.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

@Component
public class OpenIdConfigurationClient {

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final ConcurrentHashMap<String, String> jwksUriByIssuer = new ConcurrentHashMap<>();

    public OpenIdConfigurationClient(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(10000);
        this.restClient = RestClient.builder().requestFactory(factory).build();
    }

    public String resolveJwksUri(String issuer) {
        String normalized = normalizeIssuer(issuer);
        return jwksUriByIssuer.computeIfAbsent(normalized, this::fetchJwksUri);
    }

    private String fetchJwksUri(String issuer) {
        URI discovery = UriComponentsBuilder.fromUriString(issuer + "/.well-known/openid-configuration")
                .build()
                .normalize()
                .toUri();
        byte[] body = restClient.get().uri(discovery).retrieve().body(byte[].class);
        if (body == null || body.length == 0) {
            throw new IllegalStateException("Empty OpenID configuration for issuer: " + issuer);
        }
        try {
            JsonNode root = objectMapper.readTree(new String(body, StandardCharsets.UTF_8));
            JsonNode jwks = root.get("jwks_uri");
            if (jwks == null || !jwks.isTextual() || jwks.asText().isBlank()) {
                throw new IllegalStateException("jwks_uri missing in OpenID configuration for issuer: " + issuer);
            }
            return jwks.asText();
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("Failed to parse OpenID configuration for issuer: " + issuer, e);
        }
    }

    private static String normalizeIssuer(String issuer) {
        String t = issuer.trim();
        while (t.endsWith("/")) {
            t = t.substring(0, t.length() - 1);
        }
        return t;
    }
}
