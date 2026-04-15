package com.enterprise.integration;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "ImportResult", propOrder = {
        "status", "rootElementLocalName", "totalElementCount", "maxDepth", "entityCount", "message"
})
@XmlRootElement(name = "ImportResult", namespace = "http://integration.enterprise.com/soap")
public class ImportResult {

    @XmlElement(name = "status", namespace = "http://integration.enterprise.com/soap", required = true)
    private String status;

    @XmlElement(name = "rootElementLocalName", namespace = "http://integration.enterprise.com/soap")
    private String rootElementLocalName;

    @XmlElement(name = "totalElementCount", namespace = "http://integration.enterprise.com/soap")
    private long totalElementCount;

    @XmlElement(name = "maxDepth", namespace = "http://integration.enterprise.com/soap")
    private int maxDepth;

    @XmlElement(name = "entityCount", namespace = "http://integration.enterprise.com/soap")
    private long entityCount;

    @XmlElement(name = "message", namespace = "http://integration.enterprise.com/soap")
    private String message;

    public ImportResult() {
    }

    public ImportResult(String status, String rootElementLocalName, long totalElementCount,
                        int maxDepth, long entityCount, String message) {
        this.status = status;
        this.rootElementLocalName = rootElementLocalName;
        this.totalElementCount = totalElementCount;
        this.maxDepth = maxDepth;
        this.entityCount = entityCount;
        this.message = message;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getRootElementLocalName() {
        return rootElementLocalName;
    }

    public void setRootElementLocalName(String rootElementLocalName) {
        this.rootElementLocalName = rootElementLocalName;
    }

    public long getTotalElementCount() {
        return totalElementCount;
    }

    public void setTotalElementCount(long totalElementCount) {
        this.totalElementCount = totalElementCount;
    }

    public int getMaxDepth() {
        return maxDepth;
    }

    public void setMaxDepth(int maxDepth) {
        this.maxDepth = maxDepth;
    }

    public long getEntityCount() {
        return entityCount;
    }

    public void setEntityCount(long entityCount) {
        this.entityCount = entityCount;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}
