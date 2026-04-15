package com.hr.management;

import java.math.BigDecimal;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "salaryUpdateResult")
@XmlType(name = "SalaryUpdateResult")
@XmlAccessorType(XmlAccessType.FIELD)
public class SalaryUpdateResult {

    private boolean success;
    private String message;
    private String employeeId;
    private BigDecimal previousAnnualSalary;
    private BigDecimal newAnnualSalary;

    public SalaryUpdateResult() {
    }

    public SalaryUpdateResult(boolean success, String message, String employeeId,
            BigDecimal previousAnnualSalary, BigDecimal newAnnualSalary) {
        this.success = success;
        this.message = message;
        this.employeeId = employeeId;
        this.previousAnnualSalary = previousAnnualSalary;
        this.newAnnualSalary = newAnnualSalary;
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

    public BigDecimal getPreviousAnnualSalary() {
        return previousAnnualSalary;
    }

    public void setPreviousAnnualSalary(BigDecimal previousAnnualSalary) {
        this.previousAnnualSalary = previousAnnualSalary;
    }

    public BigDecimal getNewAnnualSalary() {
        return newAnnualSalary;
    }

    public void setNewAnnualSalary(BigDecimal newAnnualSalary) {
        this.newAnnualSalary = newAnnualSalary;
    }
}
