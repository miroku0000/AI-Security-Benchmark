package com.b2b.order;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "OrderLineItem", namespace = "http://b2b.order.com/soap", propOrder = {
        "sku", "unitPrice", "quantity"
})
public class OrderLineItem {

    @XmlElement(name = "sku", namespace = "http://b2b.order.com/soap", required = true)
    private String sku;

    @XmlElement(name = "unitPrice", namespace = "http://b2b.order.com/soap", required = true)
    private BigDecimal unitPrice;

    @XmlElement(name = "quantity", namespace = "http://b2b.order.com/soap", required = true)
    private int quantity;

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }
}
