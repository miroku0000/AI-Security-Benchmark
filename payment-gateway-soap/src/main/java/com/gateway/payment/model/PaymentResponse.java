package com.gateway.payment.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "PaymentResponse", namespace = "http://gateway.com/payment/ws")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "PaymentResponse", namespace = "http://gateway.com/payment/ws", propOrder = {
        "transactionId", "status", "authorizationCode", "message"
})
public class PaymentResponse {
    private String transactionId;
    private String status;
    private String authorizationCode;
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

    public String getAuthorizationCode() {
        return authorizationCode;
    }

    public void setAuthorizationCode(String authorizationCode) {
        this.authorizationCode = authorizationCode;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}
