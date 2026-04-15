package com.example.samlsp.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "saml")
public class SamlProperties {
  private Sp sp = new Sp();
  private Idp idp = new Idp();
  private long clockSkewSeconds = 120;

  public Sp getSp() {
    return sp;
  }

  public void setSp(Sp sp) {
    this.sp = sp;
  }

  public Idp getIdp() {
    return idp;
  }

  public void setIdp(Idp idp) {
    this.idp = idp;
  }

  public long getClockSkewSeconds() {
    return clockSkewSeconds;
  }

  public void setClockSkewSeconds(long clockSkewSeconds) {
    this.clockSkewSeconds = clockSkewSeconds;
  }

  public static class Sp {
    private String entityId;
    private String acsUrl;
    private Signing signing = new Signing();

    public String getEntityId() {
      return entityId;
    }

    public void setEntityId(String entityId) {
      this.entityId = entityId;
    }

    public String getAcsUrl() {
      return acsUrl;
    }

    public void setAcsUrl(String acsUrl) {
      this.acsUrl = acsUrl;
    }

    public Signing getSigning() {
      return signing;
    }

    public void setSigning(Signing signing) {
      this.signing = signing;
    }

    public static class Signing {
      private boolean enabled;
      private String keyStorePath;
      private String keyStorePassword;
      private String keyAlias;
      private String keyPassword;

      public boolean isEnabled() {
        return enabled;
      }

      public void setEnabled(boolean enabled) {
        this.enabled = enabled;
      }

      public String getKeyStorePath() {
        return keyStorePath;
      }

      public void setKeyStorePath(String keyStorePath) {
        this.keyStorePath = keyStorePath;
      }

      public String getKeyStorePassword() {
        return keyStorePassword;
      }

      public void setKeyStorePassword(String keyStorePassword) {
        this.keyStorePassword = keyStorePassword;
      }

      public String getKeyAlias() {
        return keyAlias;
      }

      public void setKeyAlias(String keyAlias) {
        this.keyAlias = keyAlias;
      }

      public String getKeyPassword() {
        return keyPassword;
      }

      public void setKeyPassword(String keyPassword) {
        this.keyPassword = keyPassword;
      }
    }
  }

  public static class Idp {
    private String entityId;
    private String ssoUrl;
    private String verificationCertPem;

    public String getEntityId() {
      return entityId;
    }

    public void setEntityId(String entityId) {
      this.entityId = entityId;
    }

    public String getSsoUrl() {
      return ssoUrl;
    }

    public void setSsoUrl(String ssoUrl) {
      this.ssoUrl = ssoUrl;
    }

    public String getVerificationCertPem() {
      return verificationCertPem;
    }

    public void setVerificationCertPem(String verificationCertPem) {
      this.verificationCertPem = verificationCertPem;
    }
  }
}

