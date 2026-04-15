package com.enterprise.oauth.client;

public record OAuthClient(
        String clientId,
        String clientSecret,
        String baseRedirectUrl
) {}
