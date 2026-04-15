package com.gateway.payment;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(
        name = "PaymentResponse",
        namespace = "http://payment.gateway.com/soap",
        propOrder = {
            "status",
            "authorizationCode",
            "detail",
            "wsuTimestampCreated",
            "wsuTimestampExpires"
        })
public class PaymentResponse {

    @XmlElement(required = true)
    private String status;

    @XmlElement
    private String authorizationCode;

    @XmlElement
    private String detail;

    @XmlElement
    private String wsuTimestampCreated;

    @XmlElement
    private String wsuTimestampExpires;

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

    public String getDetail() {
        return detail;
    }

    public void setDetail(String detail) {
        this.detail = detail;
    }

    public String getWsuTimestampCreated() {
        return wsuTimestampCreated;
    }

    public void setWsuTimestampCreated(String wsuTimestampCreated) {
        this.wsuTimestampCreated = wsuTimestampCreated;
    }

    public String getWsuTimestampExpires() {
        return wsuTimestampExpires;
    }

    public void setWsuTimestampExpires(String wsuTimestampExpires) {
        this.wsuTimestampExpires = wsuTimestampExpires;
    }
}
