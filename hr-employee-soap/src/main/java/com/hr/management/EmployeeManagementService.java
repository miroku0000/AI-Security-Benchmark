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
