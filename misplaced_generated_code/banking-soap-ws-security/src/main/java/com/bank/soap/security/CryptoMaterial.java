package com.bank.soap.security;

import java.nio.file.Path;

public final class CryptoMaterial {
  private final Path keyStorePath;
  private final char[] keyStorePassword;
  private final String keyAlias;
  private final char[] keyPassword;
  private final Path trustStorePath;
  private final char[] trustStorePassword;
  private final Path signaturePropertiesPath;
  private final Path verificationPropertiesPath;

  public CryptoMaterial(
      Path keyStorePath,
      char[] keyStorePassword,
      String keyAlias,
      char[] keyPassword,
      Path trustStorePath,
      char[] trustStorePassword,
      Path signaturePropertiesPath,
      Path verificationPropertiesPath
  ) {
    this.keyStorePath = keyStorePath;
    this.keyStorePassword = keyStorePassword;
    this.keyAlias = keyAlias;
    this.keyPassword = keyPassword;
    this.trustStorePath = trustStorePath;
    this.trustStorePassword = trustStorePassword;
    this.signaturePropertiesPath = signaturePropertiesPath;
    this.verificationPropertiesPath = verificationPropertiesPath;
  }

  public Path getKeyStorePath() {
    return keyStorePath;
  }

  public char[] getKeyStorePassword() {
    return keyStorePassword;
  }

  public String getKeyAlias() {
    return keyAlias;
  }

  public char[] getKeyPassword() {
    return keyPassword;
  }

  public Path getTrustStorePath() {
    return trustStorePath;
  }

  public char[] getTrustStorePassword() {
    return trustStorePassword;
  }

  public Path getSignaturePropertiesPath() {
    return signaturePropertiesPath;
  }

  public Path getVerificationPropertiesPath() {
    return verificationPropertiesPath;
  }
}

