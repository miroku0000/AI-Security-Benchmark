package com.example.samlsp.saml;

public class SamlException extends RuntimeException {
  public SamlException(String message) {
    super(message);
  }

  public SamlException(String message, Throwable cause) {
    super(message, cause);
  }
}

