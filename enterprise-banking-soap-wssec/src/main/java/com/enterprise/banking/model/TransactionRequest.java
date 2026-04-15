package com.enterprise.banking.model;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "transactionRequest", namespace = "http://banking.enterprise.com/types")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionRequest", namespace = "http://banking.enterprise.com/types", propOrder = {
        "correlationId", "debitAccount", "creditAccount", "amountCents", "currency", "memo"
})
public class TransactionRequest {

    @XmlElement(required = true)
    private String correlationId;
    @XmlElement(required = true)
    private String debitAccount;
    @XmlElement(required = true)
    private String creditAccount;
    @XmlElement(required = true)
    private long amountCents;
    @XmlElement(required = true)
    private String currency;
    @XmlElement
    private String memo;

    public String getCorrelationId() {
        return correlationId;
    }

    public void setCorrelationId(String correlationId) {
        this.correlationId = correlationId;
    }

    public String getDebitAccount() {
        return debitAccount;
    }

    public void setDebitAccount(String debitAccount) {
        this.debitAccount = debitAccount;
    }

    public String getCreditAccount() {
        return creditAccount;
    }

    public void setCreditAccount(String creditAccount) {
        this.creditAccount = creditAccount;
    }

    public long getAmountCents() {
        return amountCents;
    }

    public void setAmountCents(long amountCents) {
        this.amountCents = amountCents;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public String getMemo() {
        return memo;
    }

    public void setMemo(String memo) {
        this.memo = memo;
    }
}
