package com.example.mfa.web.dto;

public class MfaVerifyRequest {

  private Integer totpCode;
  private String backupCode;

  public Integer getTotpCode() {
    return totpCode;
  }

  public void setTotpCode(Integer totpCode) {
    this.totpCode = totpCode;
  }

  public String getBackupCode() {
    return backupCode;
  }

  public void setBackupCode(String backupCode) {
    this.backupCode = backupCode;
  }
}
