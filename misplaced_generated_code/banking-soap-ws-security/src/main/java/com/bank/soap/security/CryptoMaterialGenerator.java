package com.bank.soap.security;

import java.io.OutputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.security.Security;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.util.Date;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.X509v3CertificateBuilder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;

public final class CryptoMaterialGenerator {
  private CryptoMaterialGenerator() {}

  public static CryptoMaterial ensureMaterial(Path baseDir) throws Exception {
    if (Security.getProvider("BC") == null) {
      Security.addProvider(new BouncyCastleProvider());
    }

    Files.createDirectories(baseDir);

    String alias = "serverkey";
    char[] ksPass = "changeit".toCharArray();
    char[] keyPass = "changeit".toCharArray();
    char[] tsPass = "changeit".toCharArray();

    Path keyStorePath = baseDir.resolve("server-keystore.p12");
    Path trustStorePath = baseDir.resolve("server-truststore.jks");
    Path signPropsPath = baseDir.resolve("server-sign.properties");
    Path verifyPropsPath = baseDir.resolve("server-verify.properties");

    if (!Files.exists(keyStorePath) || !Files.exists(trustStorePath)) {
      KeyPair kp = generateKeyPair();
      X509Certificate cert = selfSign(kp);

      KeyStore pkcs12 = KeyStore.getInstance("PKCS12");
      pkcs12.load(null, ksPass);
      pkcs12.setKeyEntry(alias, kp.getPrivate(), keyPass, new Certificate[] { cert });
      try (OutputStream os = Files.newOutputStream(keyStorePath)) {
        pkcs12.store(os, ksPass);
      }

      KeyStore jks = KeyStore.getInstance("JKS");
      jks.load(null, tsPass);
      jks.setCertificateEntry("servercert", cert);
      try (OutputStream os = Files.newOutputStream(trustStorePath)) {
        jks.store(os, tsPass);
      }
    }

    if (!Files.exists(signPropsPath)) {
      String props = ""
          + "org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin\n"
          + "org.apache.wss4j.crypto.merlin.keystore.type=pkcs12\n"
          + "org.apache.wss4j.crypto.merlin.keystore.password=" + new String(ksPass) + "\n"
          + "org.apache.wss4j.crypto.merlin.keystore.file=" + keyStorePath.toAbsolutePath() + "\n";
      Files.writeString(signPropsPath, props, StandardCharsets.UTF_8);
    }

    if (!Files.exists(verifyPropsPath)) {
      String props = ""
          + "org.apache.wss4j.crypto.provider=org.apache.wss4j.common.crypto.Merlin\n"
          + "org.apache.wss4j.crypto.merlin.keystore.type=jks\n"
          + "org.apache.wss4j.crypto.merlin.keystore.password=" + new String(tsPass) + "\n"
          + "org.apache.wss4j.crypto.merlin.keystore.file=" + trustStorePath.toAbsolutePath() + "\n";
      Files.writeString(verifyPropsPath, props, StandardCharsets.UTF_8);
    }

    return new CryptoMaterial(
        keyStorePath, ksPass, alias, keyPass,
        trustStorePath, tsPass,
        signPropsPath, verifyPropsPath
    );
  }

  private static KeyPair generateKeyPair() throws Exception {
    KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
    kpg.initialize(2048, new SecureRandom());
    return kpg.generateKeyPair();
  }

  private static X509Certificate selfSign(KeyPair kp) throws Exception {
    Instant now = Instant.now();
    Date notBefore = Date.from(now.minusSeconds(60));
    Date notAfter = Date.from(now.plusSeconds(3650L * 24L * 60L * 60L));
    BigInteger serial = new BigInteger(160, new SecureRandom()).abs();

    X500Name subject = new X500Name("CN=BankingSOAP, OU=API, O=EnterpriseBank, L=NA, ST=NA, C=US");
    X509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
        subject, serial, notBefore, notAfter, subject, kp.getPublic()
    );

    ContentSigner signer = new JcaContentSignerBuilder("SHA256withRSA")
        .setProvider("BC")
        .build(kp.getPrivate());

    X509CertificateHolder holder = builder.build(signer);
    return new JcaX509CertificateConverter()
        .setProvider("BC")
        .getCertificate(holder);
  }
}

