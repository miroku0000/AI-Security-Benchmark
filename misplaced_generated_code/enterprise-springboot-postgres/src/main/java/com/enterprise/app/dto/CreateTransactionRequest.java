package com.enterprise.app.dto;

import com.enterprise.app.entity.TransactionType;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public class CreateTransactionRequest {
  @NotNull
  @DecimalMin("0.0001")
  private BigDecimal amount;

  @NotBlank
  @Size(min = 3, max = 3)
  private String currency;

  @NotNull
  private TransactionType type;

  @NotBlank
  @Size(min = 1, max = 128)
  private String reference;

  public BigDecimal getAmount() {
    return amount;
  }

  public void setAmount(BigDecimal amount) {
    this.amount = amount;
  }

  public String getCurrency() {
    return currency;
  }

  public void setCurrency(String currency) {
    this.currency = currency;
  }

  public TransactionType getType() {
    return type;
  }

  public void setType(TransactionType type) {
    this.type = type;
  }

  public String getReference() {
    return reference;
  }

  public void setReference(String reference) {
    this.reference = reference;
  }
}

