package com.bank.soap.model;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionRequest", propOrder = {
    "requestId",
    "fromAccount",
    "toAccount",
    "currency",
    "amount",
    "description"
})
@XmlRootElement(name = "TransactionRequest")
public class TransactionRequest {
  @XmlElement(required = true)
  private String requestId;

  @XmlElement(required = true)
  private String fromAccount;

  @XmlElement(required = true)
  private String toAccount;

  @XmlElement(required = true)
  private String currency;

  @XmlElement(required = true)
  private BigDecimal amount;

  @XmlElement(required = false)
  private String description;

  public String getRequestId() {
    return requestId;
  }

  public void setRequestId(String requestId) {
    this.requestId = requestId;
  }

  public String getFromAccount() {
    return fromAccount;
  }

  public void setFromAccount(String fromAccount) {
    this.fromAccount = fromAccount;
  }

  public String getToAccount() {
    return toAccount;
  }

  public void setToAccount(String toAccount) {
    this.toAccount = toAccount;
  }

  public String getCurrency() {
    return currency;
  }

  public void setCurrency(String currency) {
    this.currency = currency;
  }

  public BigDecimal getAmount() {
    return amount;
  }

  public void setAmount(BigDecimal amount) {
    this.amount = amount;
  }

  public String getDescription() {
    return description;
  }

  public void setDescription(String description) {
    this.description = description;
  }
}

