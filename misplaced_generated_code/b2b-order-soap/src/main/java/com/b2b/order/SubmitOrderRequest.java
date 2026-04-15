package com.b2b.order;

import java.util.ArrayList;
import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlElementWrapper;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "SubmitOrderRequest", namespace = "http://b2b.order.com/soap", propOrder = {
        "buyerAccountId", "purchaseOrderNumber", "lineItems"
})
public class SubmitOrderRequest {

    @XmlElement(name = "buyerAccountId", namespace = "http://b2b.order.com/soap", required = true)
    private String buyerAccountId;

    @XmlElement(name = "purchaseOrderNumber", namespace = "http://b2b.order.com/soap", required = true)
    private String purchaseOrderNumber;

    @XmlElementWrapper(name = "lineItems", namespace = "http://b2b.order.com/soap")
    @XmlElement(name = "lineItem", namespace = "http://b2b.order.com/soap")
    private List<OrderLineItem> lineItems = new ArrayList<>();

    public String getBuyerAccountId() {
        return buyerAccountId;
    }

    public void setBuyerAccountId(String buyerAccountId) {
        this.buyerAccountId = buyerAccountId;
    }

    public String getPurchaseOrderNumber() {
        return purchaseOrderNumber;
    }

    public void setPurchaseOrderNumber(String purchaseOrderNumber) {
        this.purchaseOrderNumber = purchaseOrderNumber;
    }

    public List<OrderLineItem> getLineItems() {
        return lineItems;
    }

    public void setLineItems(List<OrderLineItem> lineItems) {
        this.lineItems = lineItems != null ? lineItems : new ArrayList<>();
    }
}
