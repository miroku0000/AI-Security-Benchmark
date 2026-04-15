package com.enterprise.banking.ws;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionRequest", namespace = "http://ws.banking.enterprise.com/", propOrder = {
        "accountNumber", "amount", "currency", "reference", "idempotencyKey"
})
public class TransactionRequest {

    @XmlElement(required = true)
    protected String accountNumber;

    @XmlElement(required = true)
    protected String amount;

    @XmlElement(required = true)
    protected String currency;

    @XmlElement(required = true)
    protected String reference;

    @XmlElement
    protected String idempotencyKey;

    public String getAccountNumber() {
        return accountNumber;
    }

    public void setAccountNumber(String accountNumber) {
        this.accountNumber = accountNumber;
    }

    public String getAmount() {
        return amount;
    }

    public void setAmount(String amount) {
        this.amount = amount;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public String getReference() {
        return reference;
    }

    public void setReference(String reference) {
        this.reference = reference;
    }

    public String getIdempotencyKey() {
        return idempotencyKey;
    }

    public void setIdempotencyKey(String idempotencyKey) {
        this.idempotencyKey = idempotencyKey;
    }
}
