package com.enterprise.banking.model;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "transactionResponse", namespace = "http://banking.enterprise.com/types")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "TransactionResponse", namespace = "http://banking.enterprise.com/types", propOrder = {
        "transactionId", "status", "message"
})
public class TransactionResponse {

    @XmlElement(required = true)
    private String transactionId;
    @XmlElement(required = true)
    private String status;
    @XmlElement
    private String message;

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}
