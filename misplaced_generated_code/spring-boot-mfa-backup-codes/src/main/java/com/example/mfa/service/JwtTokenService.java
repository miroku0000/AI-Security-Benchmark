package com.example.mfa.service;

import com.example.mfa.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Service;

@Service
public class JwtTokenService {

  public static final String CLAIM_TYP = "typ";
  public static final String CLAIM_UID = "uid";
  public static final String TYP_ACCESS = "ACCESS";
  public static final String TYP_MFA_PENDING = "MFA_PENDING";

  private final JwtProperties jwtProperties;
  private final SecretKey secretKey;

  public JwtTokenService(JwtProperties jwtProperties) {
    this.jwtProperties = jwtProperties;
    this.secretKey = Keys.hmacShaKeyFor(jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8));
  }

  public String createAccessToken(Long userId, String username) {
    return buildToken(username, TYP_ACCESS, userId, jwtProperties.getTtlSeconds() * 1000);
  }

  public String createMfaPendingToken(Long userId, String username) {
    return buildToken(
        username, TYP_MFA_PENDING, userId, jwtProperties.getMfaPendingTtlSeconds() * 1000);
  }

  private String buildToken(String subject, String typ, Long userId, long ttlMillis) {
    Date now = new Date();
    Date exp = new Date(now.getTime() + ttlMillis);
    return Jwts.builder()
        .issuer(jwtProperties.getIssuer())
        .subject(subject)
        .claim(CLAIM_TYP, typ)
        .claim(CLAIM_UID, userId)
        .issuedAt(now)
        .expiration(exp)
        .signWith(secretKey)
        .compact();
  }

  public Claims parseClaims(String token) {
    return Jwts.parser().verifyWith(secretKey).build().parseSignedClaims(token).getPayload();
  }

  public String getSubject(String token) {
    return parseClaims(token).getSubject();
  }

  public Long getUserId(String token) {
    Object v = parseClaims(token).get(CLAIM_UID);
    if (v instanceof Number n) {
      return n.longValue();
    }
    return Long.parseLong(v.toString());
  }

  public boolean isAccessToken(String token) {
    try {
      Claims c = parseClaims(token);
      return TYP_ACCESS.equals(c.get(CLAIM_TYP, String.class));
    } catch (JwtException | IllegalArgumentException e) {
      return false;
    }
  }

  public void validateMfaPendingToken(String token) {
    Claims c = parseClaims(token);
    if (!TYP_MFA_PENDING.equals(c.get(CLAIM_TYP, String.class))) {
      throw new JwtException("Invalid MFA token");
    }
  }
}
