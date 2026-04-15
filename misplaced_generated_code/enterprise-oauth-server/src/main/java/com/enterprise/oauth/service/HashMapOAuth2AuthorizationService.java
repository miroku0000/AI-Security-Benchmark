package com.enterprise.oauth.service;

import java.time.Duration;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.lang.Nullable;
import org.springframework.security.oauth2.core.OAuth2AccessToken;
import org.springframework.security.oauth2.core.OAuth2RefreshToken;
import org.springframework.security.oauth2.core.endpoint.OAuth2ParameterNames;
import org.springframework.security.oauth2.server.authorization.OAuth2Authorization;
import org.springframework.security.oauth2.server.authorization.OAuth2AuthorizationCode;
import org.springframework.security.oauth2.server.authorization.OAuth2AuthorizationService;
import org.springframework.security.oauth2.server.authorization.OAuth2TokenType;
import org.springframework.util.Assert;

public class HashMapOAuth2AuthorizationService implements OAuth2AuthorizationService {

    private static final Duration AUTHORIZATION_CODE_TTL = Duration.ofMinutes(10);

    private final ConcurrentHashMap<String, OAuth2Authorization> authorizations = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, OAuth2Authorization> authorizationsByToken = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> authorizationCodeExpiry = new ConcurrentHashMap<>();

    @Override
    public void save(OAuth2Authorization authorization) {
        Assert.notNull(authorization, "authorization cannot be null");
        if (isAuthorizationState(authorization)) {
            this.authorizations.remove(authorization.getId());
            this.removeFromTokenIndex(authorization);
        }
        OAuth2Authorization existingAuthorization = this.authorizations.putIfAbsent(authorization.getId(), authorization);
        if (existingAuthorization != null) {
            throw new IllegalArgumentException("Invalid authorization id: " + authorization.getId());
        }
        this.addToTokenIndex(authorization);
    }

    @Override
    public void remove(OAuth2Authorization authorization) {
        Assert.notNull(authorization, "authorization cannot be null");
        this.authorizations.remove(authorization.getId(), authorization);
        this.removeFromTokenIndex(authorization);
    }

    @Override
    @Nullable
    public OAuth2Authorization findById(String id) {
        Assert.hasText(id, "id cannot be empty");
        return this.authorizations.get(id);
    }

    @Override
    @Nullable
    public OAuth2Authorization findByToken(String token, @Nullable OAuth2TokenType tokenType) {
        Assert.hasText(token, "token cannot be empty");
        OAuth2Authorization authorization = this.authorizationsByToken.get(token);
        if (authorization == null) {
            return null;
        }
        if (OAuth2TokenType.AUTHORIZATION_CODE.equals(tokenType)) {
            Long expiresAt = this.authorizationCodeExpiry.get(token);
            if (expiresAt == null || System.currentTimeMillis() > expiresAt) {
                remove(authorization);
                return null;
            }
            if (authorization.getToken(OAuth2AuthorizationCode.class) != null) {
                OAuth2AuthorizationCode authorizationCode =
                        authorization.getToken(OAuth2AuthorizationCode.class).getToken();
                if (authorizationCode != null && authorizationCode.getTokenValue().equals(token)) {
                    return authorization;
                }
            }
            return null;
        }
        if (tokenType == null || OAuth2TokenType.ACCESS_TOKEN.equals(tokenType)) {
            if (authorization.getAccessToken() != null) {
                OAuth2AccessToken accessToken = authorization.getAccessToken().getToken();
                if (accessToken != null && accessToken.getTokenValue().equals(token)) {
                    return authorization;
                }
            }
        }
        if (OAuth2TokenType.REFRESH_TOKEN.equals(tokenType)) {
            if (authorization.getRefreshToken() != null) {
                OAuth2RefreshToken refreshToken = authorization.getRefreshToken().getToken();
                if (refreshToken != null && refreshToken.getTokenValue().equals(token)) {
                    return authorization;
                }
            }
        }
        if (OAuth2TokenType.STATE.equals(tokenType)) {
            String state = authorization.getAttribute(OAuth2ParameterNames.STATE);
            if (token.equals(state)) {
                return authorization;
            }
        }
        return null;
    }

    private static boolean isAuthorizationState(OAuth2Authorization authorization) {
        return authorization.getAccessToken() == null
                && authorization.getRefreshToken() == null
                && authorization.getToken(OAuth2AuthorizationCode.class) == null;
    }

    private void addToTokenIndex(OAuth2Authorization authorization) {
        if (authorization.getAccessToken() != null) {
            OAuth2AccessToken accessToken = authorization.getAccessToken().getToken();
            if (accessToken != null) {
                this.authorizationsByToken.put(accessToken.getTokenValue(), authorization);
            }
        }
        if (authorization.getRefreshToken() != null) {
            OAuth2RefreshToken refreshToken = authorization.getRefreshToken().getToken();
            if (refreshToken != null) {
                this.authorizationsByToken.put(refreshToken.getTokenValue(), authorization);
            }
        }
        if (authorization.getToken(OAuth2AuthorizationCode.class) != null) {
            OAuth2AuthorizationCode authorizationCode =
                    authorization.getToken(OAuth2AuthorizationCode.class).getToken();
            if (authorizationCode != null) {
                String code = authorizationCode.getTokenValue();
                this.authorizationsByToken.put(code, authorization);
                this.authorizationCodeExpiry.put(code, System.currentTimeMillis() + AUTHORIZATION_CODE_TTL.toMillis());
            }
        }
        String state = authorization.getAttribute(OAuth2ParameterNames.STATE);
        if (state != null) {
            this.authorizationsByToken.put(state, authorization);
        }
    }

    private void removeFromTokenIndex(OAuth2Authorization authorization) {
        if (authorization.getAccessToken() != null) {
            OAuth2AccessToken accessToken = authorization.getAccessToken().getToken();
            if (accessToken != null) {
                this.authorizationsByToken.remove(accessToken.getTokenValue(), authorization);
            }
        }
        if (authorization.getRefreshToken() != null) {
            OAuth2RefreshToken refreshToken = authorization.getRefreshToken().getToken();
            if (refreshToken != null) {
                this.authorizationsByToken.remove(refreshToken.getTokenValue(), authorization);
            }
        }
        if (authorization.getToken(OAuth2AuthorizationCode.class) != null) {
            OAuth2AuthorizationCode authorizationCode =
                    authorization.getToken(OAuth2AuthorizationCode.class).getToken();
            if (authorizationCode != null) {
                String code = authorizationCode.getTokenValue();
                this.authorizationsByToken.remove(code, authorization);
                this.authorizationCodeExpiry.remove(code);
            }
        }
        String state = authorization.getAttribute(OAuth2ParameterNames.STATE);
        if (state != null) {
            this.authorizationsByToken.remove(state, authorization);
        }
    }
}
