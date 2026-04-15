package com.example.mfa.service;

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;
import com.warrenstrange.googleauth.GoogleAuthenticatorQRGenerator;
import org.springframework.stereotype.Service;

@Service
public class TotpService {

  private final GoogleAuthenticator googleAuthenticator = new GoogleAuthenticator();

  public GoogleAuthenticatorKey generateKey() {
    return googleAuthenticator.createCredentials();
  }

  public String buildOtpAuthUri(String issuer, String account, GoogleAuthenticatorKey key) {
    return GoogleAuthenticatorQRGenerator.getOtpAuthURL(issuer, account, key);
  }

  public boolean verify(String secret, int code) {
    return googleAuthenticator.authorize(secret, code);
  }
}
