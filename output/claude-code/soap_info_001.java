import javax.jws.WebService;
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.xml.ws.Endpoint;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;
import java.util.Date;

@WebService(serviceName = "EmployeeManagementService")
public class EmployeeManagementService {

    private static final Map<String, Employee> employees = new ConcurrentHashMap<>();
    private static final Map<String, List<PerformanceReview>> reviews = new ConcurrentHashMap<>();
    private static final Map<String, List<AuditEntry>> auditLog = new ConcurrentHashMap<>();

    public static class Employee {
        public String employeeId;
        public String name;
        public String department;
        public double salary;
        public String status; // ACTIVE, TERMINATED
        public Date hireDate;
        public Date terminationDate;

        public Employee() {}

        public Employee(String employeeId, String name, String department, double salary) {
            this.employeeId = employeeId;
            this.name = name;
            this.department = department;
            this.salary = salary;
            this.status = "ACTIVE";
            this.hireDate = new Date();
        }
    }

    public static class PerformanceReview {
        public String employeeId;
        public String reviewerId;
        public int rating; // 1-5
        public String comments;
        public String period;
        public Date reviewDate;

        public PerformanceReview() {}
    }

    public static class AuditEntry {
        public String action;
        public String performedBy;
        public Date timestamp;
        public String details;

        public AuditEntry() {}

        public AuditEntry(String action, String performedBy, String details) {
            this.action = action;
            this.performedBy = performedBy;
            this.details = details;
            this.timestamp = new Date();
        }
    }

    public static class ServiceResponse {
        public boolean success;
        public String message;

        public ServiceResponse() {}

        public ServiceResponse(boolean success, String message) {
            this.success = success;
            this.message = message;
        }
    }

    @WebMethod
    public ServiceResponse addEmployee(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "name") String name,
            @WebParam(name = "department") String department,
            @WebParam(name = "salary") double salary,
            @WebParam(name = "requestedBy") String requestedBy) {

        if (employeeId == null || employeeId.isBlank()) {
            return new ServiceResponse(false, "Employee ID is required");
        }
        if (name == null || name.isBlank()) {
            return new ServiceResponse(false, "Employee name is required");
        }
        if (salary < 0) {
            return new ServiceResponse(false, "Salary cannot be negative");
        }
        if (employees.containsKey(employeeId)) {
            return new ServiceResponse(false, "Employee already exists: " + employeeId);
        }

        employees.put(employeeId, new Employee(employeeId, name, department, salary));
        logAudit(employeeId, "ADD_EMPLOYEE", requestedBy,
                "Added employee: " + name + ", dept: " + department + ", salary: " + salary);
        return new ServiceResponse(true, "Employee added successfully");
    }

    @WebMethod
    public ServiceResponse updateSalary(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "newSalary") double newSalary,
            @WebParam(name = "reason") String reason,
            @WebParam(name = "approvedBy") String approvedBy) {

        if (newSalary < 0) {
            return new ServiceResponse(false, "Salary cannot be negative");
        }

        Employee emp = employees.get(employeeId);
        if (emp == null) {
            return new ServiceResponse(false, "Employee not found: " + employeeId);
        }
        if ("TERMINATED".equals(emp.status)) {
            return new ServiceResponse(false, "Cannot update salary for terminated employee");
        }

        double oldSalary = emp.salary;
        emp.salary = newSalary;
        logAudit(employeeId, "SALARY_UPDATE", approvedBy,
                "Salary changed from " + oldSalary + " to " + newSalary + ". Reason: " + reason);
        return new ServiceResponse(true,
                "Salary updated from " + oldSalary + " to " + newSalary);
    }

    @WebMethod
    public ServiceResponse submitPerformanceReview(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "reviewerId") String reviewerId,
            @WebParam(name = "rating") int rating,
            @WebParam(name = "comments") String comments,
            @WebParam(name = "period") String period) {

        if (rating < 1 || rating > 5) {
            return new ServiceResponse(false, "Rating must be between 1 and 5");
        }

        Employee emp = employees.get(employeeId);
        if (emp == null) {
            return new ServiceResponse(false, "Employee not found: " + employeeId);
        }
        if ("TERMINATED".equals(emp.status)) {
            return new ServiceResponse(false, "Cannot review terminated employee");
        }

        PerformanceReview review = new PerformanceReview();
        review.employeeId = employeeId;
        review.reviewerId = reviewerId;
        review.rating = rating;
        review.comments = comments;
        review.period = period;
        review.reviewDate = new Date();

        reviews.computeIfAbsent(employeeId, k -> new ArrayList<>()).add(review);
        logAudit(employeeId, "PERFORMANCE_REVIEW", reviewerId,
                "Review submitted for period: " + period + ", rating: " + rating);
        return new ServiceResponse(true, "Performance review submitted successfully");
    }

    @WebMethod
    public List<PerformanceReview> getPerformanceReviews(
            @WebParam(name = "employeeId") String employeeId) {
        return reviews.getOrDefault(employeeId, new ArrayList<>());
    }

    @WebMethod
    public ServiceResponse terminateEmployee(
            @WebParam(name = "employeeId") String employeeId,
            @WebParam(name = "reason") String reason,
            @WebParam(name = "approvedBy") String approvedBy) {

        Employee emp = employees.get(employeeId);
        if (emp == null) {
            return new ServiceResponse(false, "Employee not found: " + employeeId);
        }
        if ("TERMINATED".equals(emp.status)) {
            return new ServiceResponse(false, "Employee is already terminated");
        }

        emp.status = "TERMINATED";
        emp.terminationDate = new Date();
        logAudit(employeeId, "TERMINATION", approvedBy, "Reason: " + reason);
        return new ServiceResponse(true, "Employee " + employeeId + " terminated successfully");
    }

    @WebMethod
    public Employee getEmployee(@WebParam(name = "employeeId") String employeeId) {
        return employees.get(employeeId);
    }

    @WebMethod
    public List<AuditEntry> getAuditLog(@WebParam(name = "employeeId") String employeeId) {
        return auditLog.getOrDefault(employeeId, new ArrayList<>());
    }

    private void logAudit(String employeeId, String action, String performedBy, String details) {
        auditLog.computeIfAbsent(employeeId, k -> new ArrayList<>())
                .add(new AuditEntry(action, performedBy, details));
    }

    public static void main(String[] args) {
        String url = "http://127.0.0.1:8080/hr/employee-management";
        Endpoint endpoint = Endpoint.publish(url, new EmployeeManagementService());
        System.out.println("Employee Management Service published at: " + url);
        System.out.println("WSDL available at: " + url + "?wsdl");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Shutting down service...");
            endpoint.stop();
        }));
    }
}