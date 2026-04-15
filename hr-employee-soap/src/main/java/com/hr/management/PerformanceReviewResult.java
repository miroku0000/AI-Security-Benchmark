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
