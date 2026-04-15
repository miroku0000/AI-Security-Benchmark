package com.hr.management;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "terminationResult")
@XmlType(name = "TerminationResult")
@XmlAccessorType(XmlAccessType.FIELD)
public class TerminationResult {

    private boolean success;
    private String message;
    private String employeeId;
    private String terminationId;
    private String effectiveDate;
    private String status;

    public TerminationResult() {
    }

    public TerminationResult(boolean success, String message, String employeeId,
            String terminationId, String effectiveDate, String status) {
        this.success = success;
        this.message = message;
        this.employeeId = employeeId;
        this.terminationId = terminationId;
        this.effectiveDate = effectiveDate;
        this.status = status;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getEmployeeId() {
        return employeeId;
    }

    public void setEmployeeId(String employeeId) {
        this.employeeId = employeeId;
    }

    public String getTerminationId() {
        return terminationId;
    }

    public void setTerminationId(String terminationId) {
        this.terminationId = terminationId;
    }

    public String getEffectiveDate() {
        return effectiveDate;
    }

    public void setEffectiveDate(String effectiveDate) {
        this.effectiveDate = effectiveDate;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
