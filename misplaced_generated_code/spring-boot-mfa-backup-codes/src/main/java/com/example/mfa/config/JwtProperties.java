package com.example.mfa.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.jwt")
public class JwtProperties {

  private String issuer = "enterprise-auth";
  private String secret = "";
  private long ttlSeconds = 3600;
  private long mfaPendingTtlSeconds = 300;

  public String getIssuer() {
    return issuer;
  }

  public void setIssuer(String issuer) {
    this.issuer = issuer;
  }

  public String getSecret() {
    return secret;
  }

  public void setSecret(String secret) {
    this.secret = secret;
  }

  public long getTtlSeconds() {
    return ttlSeconds;
  }

  public void setTtlSeconds(long ttlSeconds) {
    this.ttlSeconds = ttlSeconds;
  }

  public long getMfaPendingTtlSeconds() {
    return mfaPendingTtlSeconds;
  }

  public void setMfaPendingTtlSeconds(long mfaPendingTtlSeconds) {
    this.mfaPendingTtlSeconds = mfaPendingTtlSeconds;
  }
}
