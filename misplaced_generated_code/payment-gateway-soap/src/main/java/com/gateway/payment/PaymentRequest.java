package com.gateway.payment;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(
        name = "PaymentRequest",
        namespace = "http://payment.gateway.com/soap",
        propOrder = {"merchantId", "transactionId", "amount", "currency", "instrumentToken"})
public class PaymentRequest {

    @XmlElement(required = true)
    private String merchantId;

    @XmlElement(required = true)
    private String transactionId;

    @XmlElement(required = true)
    private BigDecimal amount;

    @XmlElement(required = true)
    private String currency;

    @XmlElement(required = true)
    private String instrumentToken;

    public String getMerchantId() {
        return merchantId;
    }

    public void setMerchantId(String merchantId) {
        this.merchantId = merchantId;
    }

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

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

    public String getInstrumentToken() {
        return instrumentToken;
    }

    public void setInstrumentToken(String instrumentToken) {
        this.instrumentToken = instrumentToken;
    }
}
