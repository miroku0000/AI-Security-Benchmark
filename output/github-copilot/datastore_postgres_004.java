package com.enterprise.app;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class EnterpriseApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseApplication.class, args);
    }
}

// src/main/java/com/enterprise/app/domain/UserStatus.java
package com.enterprise.app.domain;

public enum UserStatus {
    ACTIVE,
    INACTIVE,
    SUSPENDED
}

// src/main/java/com/enterprise/app/domain/TransactionType.java
package com.enterprise.app.domain;

public enum TransactionType {
    CREDIT,
    DEBIT
}

// src/main/java/com/enterprise/app/domain/TransactionStatus.java
package com.enterprise.app.domain;

public enum TransactionStatus {
    COMPLETED,
    FAILED
}

// src/main/java/com/enterprise/app/domain/UserAccount.java
package com.enterprise.app.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "user_accounts")
public class UserAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false, unique = true, length = 150)
    private String email;

    @Column(nullable = false, length = 150)
    private String fullName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private UserStatus status = UserStatus.ACTIVE;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal balance = BigDecimal.ZERO;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        createdAt = now;
        updatedAt = now;
        if (status == null) {
            status = UserStatus.ACTIVE;
        }
        if (balance == null) {
            balance = BigDecimal.ZERO;
        }
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public UserStatus getStatus() {
        return status;
    }

    public void setStatus(UserStatus status) {
        this.status = status;
    }

    public BigDecimal getBalance() {
        return balance;
    }

    public void setBalance(BigDecimal balance) {
        this.balance = balance;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}

// src/main/java/com/enterprise/app/domain/TransactionRecord.java
package com.enterprise.app.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "transaction_records")
public class TransactionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 64)
    private String referenceCode;

    @ManyToOne(optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private UserAccount user;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private TransactionType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private TransactionStatus status;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal resultingBalance;

    @Column(nullable = false, length = 255)
    private String description;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime processedAt;

    @PrePersist
    void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        createdAt = now;
        if (processedAt == null) {
            processedAt = now;
        }
    }

    public Long getId() {
        return id;
    }

    public String getReferenceCode() {
        return referenceCode;
    }

    public void setReferenceCode(String referenceCode) {
        this.referenceCode = referenceCode;
    }

    public UserAccount getUser() {
        return user;
    }

    public void setUser(UserAccount user) {
        this.user = user;
    }

    public TransactionType getType() {
        return type;
    }

    public void setType(TransactionType type) {
        this.type = type;
    }

    public TransactionStatus getStatus() {
        return status;
    }

    public void setStatus(TransactionStatus status) {
        this.status = status;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public BigDecimal getResultingBalance() {
        return resultingBalance;
    }

    public void setResultingBalance(BigDecimal resultingBalance) {
        this.resultingBalance = resultingBalance;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getProcessedAt() {
        return processedAt;
    }

    public void setProcessedAt(LocalDateTime processedAt) {
        this.processedAt = processedAt;
    }
}

// src/main/java/com/enterprise/app/repository/UserAccountRepository.java
package com.enterprise.app.repository;

import com.enterprise.app.domain.UserAccount;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserAccountRepository extends JpaRepository<UserAccount, Long> {

    boolean existsByUsernameIgnoreCase(String username);

    boolean existsByEmailIgnoreCase(String email);

    Optional<UserAccount> findByUsernameIgnoreCase(String username);
}

// src/main/java/com/enterprise/app/repository/TransactionRecordRepository.java
package com.enterprise.app.repository;

import com.enterprise.app.domain.TransactionRecord;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TransactionRecordRepository extends JpaRepository<TransactionRecord, Long> {

    List<TransactionRecord> findAllByOrderByProcessedAtDesc();

    List<TransactionRecord> findByUserIdOrderByProcessedAtDesc(Long userId);

    Optional<TransactionRecord> findByReferenceCode(String referenceCode);
}

// src/main/java/com/enterprise/app/api/dto/CreateUserRequest.java
package com.enterprise.app.api.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateUserRequest(
        @NotBlank @Size(max = 50) String username,
        @NotBlank @Email @Size(max = 150) String email,
        @NotBlank @Size(max = 150) String fullName) {
}

// src/main/java/com/enterprise/app/api/dto/UpdateUserRequest.java
package com.enterprise.app.api.dto;

import com.enterprise.app.domain.UserStatus;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;

public record UpdateUserRequest(
        @Size(max = 150) String fullName,
        @Email @Size(max = 150) String email,
        UserStatus status) {
}

// src/main/java/com/enterprise/app/api/dto/UserResponse.java
package com.enterprise.app.api.dto;

import com.enterprise.app.domain.UserStatus;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public record UserResponse(
        Long id,
        String username,
        String email,
        String fullName,
        UserStatus status,
        BigDecimal balance,
        LocalDateTime createdAt,
        LocalDateTime updatedAt) {
}

// src/main/java/com/enterprise/app/api/dto/ProcessTransactionRequest.java
package com.enterprise.app.api.dto;

import com.enterprise.app.domain.TransactionType;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record ProcessTransactionRequest(
        @NotNull Long userId,
        @NotNull TransactionType type,
        @NotNull @DecimalMin(value = "0.01") BigDecimal amount,
        @NotBlank @Size(max = 255) String description) {
}

// src/main/java/com/enterprise/app/api/dto/TransactionResponse.java
package com.enterprise.app.api.dto;

import com.enterprise.app.domain.TransactionStatus;
import com.enterprise.app.domain.TransactionType;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public record TransactionResponse(
        Long id,
        String referenceCode,
        Long userId,
        String username,
        TransactionType type,
        TransactionStatus status,
        BigDecimal amount,
        BigDecimal resultingBalance,
        String description,
        LocalDateTime createdAt,
        LocalDateTime processedAt) {
}

// src/main/java/com/enterprise/app/api/dto/ErrorResponse.java
package com.enterprise.app.api.dto;

import java.time.LocalDateTime;
import java.util.List;

public record ErrorResponse(
        LocalDateTime timestamp,
        int status,
        String error,
        String message,
        String path,
        List<String> details) {
}

// src/main/java/com/enterprise/app/exception/ResourceNotFoundException.java
package com.enterprise.app.exception;

public class ResourceNotFoundException extends RuntimeException {

    public ResourceNotFoundException(String message) {
        super(message);
    }
}

// src/main/java/com/enterprise/app/exception/DuplicateResourceException.java
package com.enterprise.app.exception;

public class DuplicateResourceException extends RuntimeException {

    public DuplicateResourceException(String message) {
        super(message);
    }
}

// src/main/java/com/enterprise/app/exception/InsufficientFundsException.java
package com.enterprise.app.exception;

public class InsufficientFundsException extends RuntimeException {

    public InsufficientFundsException(String message) {
        super(message);
    }
}

// src/main/java/com/enterprise/app/service/UserAccountService.java
package com.enterprise.app.service;

import com.enterprise.app.api.dto.CreateUserRequest;
import com.enterprise.app.api.dto.UpdateUserRequest;
import com.enterprise.app.domain.UserAccount;
import com.enterprise.app.exception.DuplicateResourceException;
import com.enterprise.app.exception.ResourceNotFoundException;
import com.enterprise.app.repository.UserAccountRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserAccountService {

    private final UserAccountRepository userAccountRepository;

    public UserAccountService(UserAccountRepository userAccountRepository) {
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional
    public UserAccount createUser(CreateUserRequest request) {
        String normalizedUsername = request.username().trim();
        String normalizedEmail = request.email().trim().toLowerCase();
        String normalizedFullName = request.fullName().trim();

        if (userAccountRepository.existsByUsernameIgnoreCase(normalizedUsername)) {
            throw new DuplicateResourceException("Username already exists: " + normalizedUsername);
        }
        if (userAccountRepository.existsByEmailIgnoreCase(normalizedEmail)) {
            throw new DuplicateResourceException("Email already exists: " + normalizedEmail);
        }

        UserAccount user = new UserAccount();
        user.setUsername(normalizedUsername);
        user.setEmail(normalizedEmail);
        user.setFullName(normalizedFullName);
        return userAccountRepository.save(user);
    }

    @Transactional(readOnly = true)
    public List<UserAccount> getAllUsers() {
        return userAccountRepository.findAll();
    }

    @Transactional(readOnly = true)
    public UserAccount getUser(Long id) {
        return userAccountRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User not found: " + id));
    }

    @Transactional
    public UserAccount updateUser(Long id, UpdateUserRequest request) {
        UserAccount user = getUser(id);

        if (request.email() != null) {
            String normalizedEmail = request.email().trim().toLowerCase();
            if (!normalizedEmail.equalsIgnoreCase(user.getEmail())
                    && userAccountRepository.existsByEmailIgnoreCase(normalizedEmail)) {
                throw new DuplicateResourceException("Email already exists: " + normalizedEmail);
            }
            user.setEmail(normalizedEmail);
        }

        if (request.fullName() != null) {
            user.setFullName(request.fullName().trim());
        }

        if (request.status() != null) {
            user.setStatus(request.status());
        }

        return userAccountRepository.save(user);
    }
}

// src/main/java/com/enterprise/app/service/TransactionService.java
package com.enterprise.app.service;

import com.enterprise.app.api.dto.ProcessTransactionRequest;
import com.enterprise.app.domain.TransactionRecord;
import com.enterprise.app.domain.TransactionStatus;
import com.enterprise.app.domain.TransactionType;
import com.enterprise.app.domain.UserAccount;
import com.enterprise.app.domain.UserStatus;
import com.enterprise.app.exception.InsufficientFundsException;
import com.enterprise.app.exception.ResourceNotFoundException;
import com.enterprise.app.repository.TransactionRecordRepository;
import com.enterprise.app.repository.UserAccountRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TransactionService {

    private final TransactionRecordRepository transactionRecordRepository;
    private final UserAccountRepository userAccountRepository;

    public TransactionService(TransactionRecordRepository transactionRecordRepository,
                              UserAccountRepository userAccountRepository) {
        this.transactionRecordRepository = transactionRecordRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional
    public TransactionRecord processTransaction(ProcessTransactionRequest request) {
        UserAccount user = userAccountRepository.findById(request.userId())
                .orElseThrow(() -> new ResourceNotFoundException("User not found: " + request.userId()));

        if (user.getStatus() != UserStatus.ACTIVE) {
            throw new IllegalStateException("Transactions can only be processed for active users");
        }

        BigDecimal currentBalance = user.getBalance() == null ? BigDecimal.ZERO : user.getBalance();
        BigDecimal amount = request.amount().setScale(2, RoundingMode.HALF_UP);
        BigDecimal updatedBalance;

        if (request.type() == TransactionType.CREDIT) {
            updatedBalance = currentBalance.add(amount);
        } else {
            if (currentBalance.compareTo(amount) < 0) {
                throw new InsufficientFundsException("Insufficient funds for debit transaction");
            }
            updatedBalance = currentBalance.subtract(amount);
        }

        user.setBalance(updatedBalance);
        userAccountRepository.save(user);

        TransactionRecord transaction = new TransactionRecord();
        transaction.setReferenceCode(generateReferenceCode());
        transaction.setUser(user);
        transaction.setType(request.type());
        transaction.setStatus(TransactionStatus.COMPLETED);
        transaction.setAmount(amount);
        transaction.setResultingBalance(updatedBalance);
        transaction.setDescription(request.description().trim());
        transaction.setProcessedAt(LocalDateTime.now());

        return transactionRecordRepository.save(transaction);
    }

    @Transactional(readOnly = true)
    public List<TransactionRecord> getAllTransactions() {
        return transactionRecordRepository.findAllByOrderByProcessedAtDesc();
    }

    @Transactional(readOnly = true)
    public List<TransactionRecord> getTransactionsForUser(Long userId) {
        if (!userAccountRepository.existsById(userId)) {
            throw new ResourceNotFoundException("User not found: " + userId);
        }
        return transactionRecordRepository.findByUserIdOrderByProcessedAtDesc(userId);
    }

    @Transactional(readOnly = true)
    public TransactionRecord getTransactionByReferenceCode(String referenceCode) {
        return transactionRecordRepository.findByReferenceCode(referenceCode)
                .orElseThrow(() -> new ResourceNotFoundException("Transaction not found: " + referenceCode));
    }

    private String generateReferenceCode() {
        return "TXN-" + UUID.randomUUID().toString().replace("-", "").toUpperCase();
    }
}

// src/main/java/com/enterprise/app/api/UserAccountController.java
package com.enterprise.app.api;

import com.enterprise.app.api.dto.CreateUserRequest;
import com.enterprise.app.api.dto.UpdateUserRequest;
import com.enterprise.app.api.dto.UserResponse;
import com.enterprise.app.domain.UserAccount;
import com.enterprise.app.service.UserAccountService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
public class UserAccountController {

    private final UserAccountService userAccountService;

    public UserAccountController(UserAccountService userAccountService) {
        this.userAccountService = userAccountService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(@Valid @RequestBody CreateUserRequest request) {
        return toResponse(userAccountService.createUser(request));
    }

    @GetMapping
    public List<UserResponse> getUsers() {
        return userAccountService.getAllUsers().stream()
                .map(this::toResponse)
                .toList();
    }

    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) {
        return toResponse(userAccountService.getUser(id));
    }

    @PutMapping("/{id}")
    public UserResponse updateUser(@PathVariable Long id, @Valid @RequestBody UpdateUserRequest request) {
        return toResponse(userAccountService.updateUser(id, request));
    }

    private UserResponse toResponse(UserAccount user) {
        return new UserResponse(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getFullName(),
                user.getStatus(),
                user.getBalance(),
                user.getCreatedAt(),
                user.getUpdatedAt());
    }
}

// src/main/java/com/enterprise/app/api/TransactionController.java
package com.enterprise.app.api;

import com.enterprise.app.api.dto.ProcessTransactionRequest;
import com.enterprise.app.api.dto.TransactionResponse;
import com.enterprise.app.domain.TransactionRecord;
import com.enterprise.app.service.TransactionService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/transactions")
public class TransactionController {

    private final TransactionService transactionService;

    public TransactionController(TransactionService transactionService) {
        this.transactionService = transactionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TransactionResponse processTransaction(@Valid @RequestBody ProcessTransactionRequest request) {
        return toResponse(transactionService.processTransaction(request));
    }

    @GetMapping
    public List<TransactionResponse> getTransactions() {
        return transactionService.getAllTransactions().stream()
                .map(this::toResponse)
                .toList();
    }

    @GetMapping("/user/{userId}")
    public List<TransactionResponse> getTransactionsForUser(@PathVariable Long userId) {
        return transactionService.getTransactionsForUser(userId).stream()
                .map(this::toResponse)
                .toList();
    }

    @GetMapping("/{referenceCode}")
    public TransactionResponse getTransaction(@PathVariable String referenceCode) {
        return toResponse(transactionService.getTransactionByReferenceCode(referenceCode));
    }

    private TransactionResponse toResponse(TransactionRecord transaction) {
        return new TransactionResponse(
                transaction.getId(),
                transaction.getReferenceCode(),
                transaction.getUser().getId(),
                transaction.getUser().getUsername(),
                transaction.getType(),
                transaction.getStatus(),
                transaction.getAmount(),
                transaction.getResultingBalance(),
                transaction.getDescription(),
                transaction.getCreatedAt(),
                transaction.getProcessedAt());
    }
}

// src/main/java/com/enterprise/app/api/GlobalExceptionHandler.java
package com.enterprise.app.api;

import com.enterprise.app.api.dto.ErrorResponse;
import com.enterprise.app.exception.DuplicateResourceException;
import com.enterprise.app.exception.InsufficientFundsException;
import com.enterprise.app.exception.ResourceNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        return buildResponse(HttpStatus.NOT_FOUND, ex.getMessage(), request.getRequestURI(), List.of());
    }

    @ExceptionHandler(DuplicateResourceException.class)
    public ResponseEntity<ErrorResponse> handleConflict(DuplicateResourceException ex, HttpServletRequest request) {
        return buildResponse(HttpStatus.CONFLICT, ex.getMessage(), request.getRequestURI(), List.of());
    }

    @ExceptionHandler(InsufficientFundsException.class)
    public ResponseEntity<ErrorResponse> handleInsufficientFunds(InsufficientFundsException ex,
                                                                 HttpServletRequest request) {
        return buildResponse(HttpStatus.BAD_REQUEST, ex.getMessage(), request.getRequestURI(), List.of());
    }

    @ExceptionHandler({IllegalStateException.class, ConstraintViolationException.class})
    public ResponseEntity<ErrorResponse> handleBusinessError(RuntimeException ex, HttpServletRequest request) {
        return buildResponse(HttpStatus.BAD_REQUEST, ex.getMessage(), request.getRequestURI(), List.of());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex,
                                                          HttpServletRequest request) {
        List<String> details = ex.getBindingResult().getFieldErrors().stream()
                .map(this::formatFieldError)
                .toList();
        return buildResponse(HttpStatus.BAD_REQUEST, "Validation failed", request.getRequestURI(), details);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleUnreadableMessage(HttpMessageNotReadableException ex,
                                                                 HttpServletRequest request) {
        return buildResponse(HttpStatus.BAD_REQUEST, "Malformed request payload", request.getRequestURI(), List.of());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnhandled(Exception ex, HttpServletRequest request) {
        return buildResponse(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "An unexpected error occurred",
                request.getRequestURI(),
                List.of());
    }

    private String formatFieldError(FieldError error) {
        return error.getField() + ": " + error.getDefaultMessage();
    }

    private ResponseEntity<ErrorResponse> buildResponse(HttpStatus status,
                                                        String message,
                                                        String path,
                                                        List<String> details) {
        ErrorResponse body = new ErrorResponse(
                LocalDateTime.now(),
                status.value(),
                status.getReasonPhrase(),
                message,
                path,
                details);
        return ResponseEntity.status(status).body(body);
    }
}

// src/test/java/com/enterprise/app/EnterpriseApplicationTests.java
package com.enterprise.app;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class EnterpriseApplicationTests {

    @Test
    void contextLoads() {
    }
}