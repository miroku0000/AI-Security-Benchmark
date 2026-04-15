package com.example.samlsp.saml;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Base64;

public final class PemUtils {
  private PemUtils() {}

  public static X509Certificate parseX509CertificateFromPem(String pem) throws CertificateException {
    if (pem == null) {
      throw new CertificateException("PEM is null");
    }
    String normalized = pem
        .replace("\r", "")
        .replace("-----BEGIN CERTIFICATE-----", "")
        .replace("-----END CERTIFICATE-----", "")
        .replaceAll("\\s+", "");
    byte[] der = Base64.getDecoder().decode(normalized.getBytes(StandardCharsets.US_ASCII));
    CertificateFactory cf = CertificateFactory.getInstance("X.509");
    return (X509Certificate) cf.generateCertificate(new ByteArrayInputStream(der));
  }
}

