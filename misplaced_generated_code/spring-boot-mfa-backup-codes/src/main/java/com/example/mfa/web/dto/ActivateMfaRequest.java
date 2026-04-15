package com.example.mfa.web.dto;

import jakarta.validation.constraints.NotNull;

public class ActivateMfaRequest {

  @NotNull
  private Integer totpCode;

  public Integer getTotpCode() {
    return totpCode;
  }

  public void setTotpCode(Integer totpCode) {
    this.totpCode = totpCode;
  }
}
