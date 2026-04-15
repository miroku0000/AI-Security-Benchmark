package com.b2b.order;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "OrderProcessingResult", namespace = "http://b2b.order.com/soap", propOrder = {
        "orderId", "totalAmount", "status", "message"
})
public class OrderProcessingResult {

    @XmlElement(name = "orderId", namespace = "http://b2b.order.com/soap", required = true)
    private String orderId;

    @XmlElement(name = "totalAmount", namespace = "http://b2b.order.com/soap", required = true)
    private BigDecimal totalAmount;

    @XmlElement(name = "status", namespace = "http://b2b.order.com/soap", required = true)
    private String status;

    @XmlElement(name = "message", namespace = "http://b2b.order.com/soap")
    private String message;

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(BigDecimal totalAmount) {
        this.totalAmount = totalAmount;
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
