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
