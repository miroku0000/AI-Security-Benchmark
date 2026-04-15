package com.example.oidcclient;

import java.io.Serializable;
import java.time.Instant;
import java.util.Map;

public record UserSession(
    String subject,
    String issuer,
    String email,
    String name,
    Instant issuedAt,
    Instant expiresAt,
    Map<String, Object> idTokenClaims,
    Map<String, Object> userInfoClaims,
    String accessToken
) implements Serializable {}

