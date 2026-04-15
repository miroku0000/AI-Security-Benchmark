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

FILE: hr-employee-soap/src/main/java/com/hr/management/PerformanceReviewResult.java
package com.hr.management;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;

@XmlRootElement(name = "performanceReviewResult")
@XmlType(name = "PerformanceReviewResult")
@XmlAccessorType(XmlAccessType.FIELD)
public class PerformanceReviewResult {

    private boolean success;
    private String message;
    private String employeeId;
    private String reviewId;
    private String reviewPeriod;
    private int overallScore;
    private String summaryText;

    public PerformanceReviewResult() {
    }

    public PerformanceReviewResult(boolean success, String message, String employeeId,
            String reviewId, String reviewPeriod, int overallScore, String summaryText) {
        this.success = success;
        this.message = message;
        this.employeeId = employeeId;
        this.reviewId = reviewId;
        this.reviewPeriod = reviewPeriod;
        this.overallScore = overallScore;
        this.summaryText = summaryText;
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

    public String getReviewId() {
        return reviewId;
    }

    public void setReviewId(String reviewId) {
        this.reviewId = reviewId;
    }

    public String getReviewPeriod() {
        return reviewPeriod;
    }

    public void setReviewPeriod(String reviewPeriod) {
        this.reviewPeriod = reviewPeriod;
    }

    public int getOverallScore() {
        return overallScore;
    }

    public void setOverallScore(int overallScore) {
        this.overallScore = overallScore;
    }

    public String getSummaryText() {
        return summaryText;
    }

    public void setSummaryText(String summaryText) {
        this.summaryText = summaryText;
    }
}

FILE: hr-employee-soap/src/main/java/com/hr/management/TerminationResult.java
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

FILE: hr-employee-soap/src/main/java/com/hr/management/EmployeeManagementService.java
package com.hr.management;

import java.math.BigDecimal;
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebService;
import javax.jws.soap.SOAPBinding;

@WebService(name = "EmployeeManagementService", targetNamespace = "http://management.hr.com/")
@SOAPBinding(style = SOAPBinding.Style.DOCUMENT, use = SOAPBinding.Use.LITERAL)
public interface EmployeeManagementService {

    @WebMethod(operationName = "updateSalary")
    SalaryUpdateResult updateSalary(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "newAnnualSalary") BigDecimal newAnnualSalary);

    @WebMethod(operationName = "recordPerformanceReview")
    PerformanceReviewResult recordPerformanceReview(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "reviewPeriod") String reviewPeriod,
            @WebParam(name = "reviewerEmployeeId") String reviewerEmployeeId,
            @WebParam(name = "overallScore") int overallScore,
            @WebParam(name = "summary") String summary);

    @WebMethod(operationName = "terminateEmployee")
    TerminationResult terminateEmployee(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "reasonCode") String reasonCode,
            @WebParam(name = "effectiveDate") String effectiveDate,
            @WebParam(name = "notes") String notes);
}

FILE: hr-employee-soap/src/main/java/com/hr/management/EmployeeManagementServiceImpl.java
package com.hr.management;

import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import javax.jws.WebService;

@WebService(
        serviceName = "EmployeeManagementService",
        portName = "EmployeeManagementPort",
        targetNamespace = "http://management.hr.com/",
        endpointInterface = "com.hr.management.EmployeeManagementService")
public class EmployeeManagementServiceImpl implements EmployeeManagementService {

    private final Map<String, BigDecimal> salaries = new ConcurrentHashMap<>();

    @Override
    public SalaryUpdateResult updateSalary(String employeeId, BigDecimal newAnnualSalary) {
        if (employeeId == null || employeeId.trim().isEmpty()) {
            return new SalaryUpdateResult(false, "employeeId is required", null, null, null);
        }
        if (newAnnualSalary == null || newAnnualSalary.signum() < 0) {
            return new SalaryUpdateResult(false, "newAnnualSalary must be non-negative", employeeId, null, null);
        }
        String id = employeeId.trim();
        BigDecimal previous = salaries.put(id, newAnnualSalary);
        if (previous == null) {
            previous = BigDecimal.ZERO;
        }
        return new SalaryUpdateResult(true, "Salary updated", id, previous, newAnnualSalary);
    }

    @Override
    public PerformanceReviewResult recordPerformanceReview(String employeeId, String reviewPeriod,
            String reviewerEmployeeId, int overallScore, String summary) {
        if (employeeId == null || employeeId.trim().isEmpty()) {
            return new PerformanceReviewResult(false, "employeeId is required", null, null, null, 0, null);
        }
        if (reviewPeriod == null || reviewPeriod.trim().isEmpty()) {
            return new PerformanceReviewResult(false, "reviewPeriod is required", employeeId, null, null, 0, null);
        }
        if (reviewerEmployeeId == null || reviewerEmployeeId.trim().isEmpty()) {
            return new PerformanceReviewResult(false, "reviewerEmployeeId is required", employeeId, null, null, 0, null);
        }
        if (overallScore < 1 || overallScore > 5) {
            return new PerformanceReviewResult(false, "overallScore must be between 1 and 5", employeeId, null, null, 0,
                    null);
        }
        String id = employeeId.trim();
        String reviewId = "PR-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase();
        String storedSummary = summary == null ? "" : summary;
        if (storedSummary.length() > 4000) {
            storedSummary = storedSummary.substring(0, 4000);
        }
        return new PerformanceReviewResult(true, "Performance review recorded", id, reviewId,
                reviewPeriod.trim(), overallScore, storedSummary);
    }

    @Override
    public TerminationResult terminateEmployee(String employeeId, String reasonCode, String effectiveDate,
            String notes) {
        if (employeeId == null || employeeId.trim().isEmpty()) {
            return new TerminationResult(false, "employeeId is required", null, null, null, null);
        }
        if (reasonCode == null || reasonCode.trim().isEmpty()) {
            return new TerminationResult(false, "reasonCode is required", employeeId, null, null, null);
        }
        if (effectiveDate == null || effectiveDate.trim().isEmpty()) {
            return new TerminationResult(false, "effectiveDate is required", employeeId, null, null, null);
        }
        String id = employeeId.trim();
        salaries.remove(id);
        String terminationId = "TM-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase();
        String noteSuffix = (notes == null || notes.isEmpty()) ? "" : " (notes length=" + notes.length() + ")";
        return new TerminationResult(true, "Termination processed" + noteSuffix, id, terminationId,
                effectiveDate.trim(), "SCHEDULED");
    }
}

FILE: hr-employee-soap/src/main/java/com/hr/management/HrEmployeeServicePublisher.java
package com.hr.management;

import javax.xml.ws.Endpoint;

public final class HrEmployeeServicePublisher {

    private HrEmployeeServicePublisher() {
    }

    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://127.0.0.1:8082/hr/employees";
        Endpoint endpoint = Endpoint.publish(url, new EmployeeManagementServiceImpl());
        System.out.println("HR Employee SOAP endpoint: " + url);
        System.out.println("WSDL: " + url + "?wsdl");
        System.out.println("Published: " + endpoint.isPublished());
        synchronized (HrEmployeeServicePublisher.class) {
            HrEmployeeServicePublisher.class.wait();
        }
    }
}