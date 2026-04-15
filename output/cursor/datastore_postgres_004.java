import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class EnterpriseApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseApplication.class, args);
    }
}
<<<END src/main/java/com/enterprise/app/EnterpriseApplication.java>>>

<<<BEGIN src/main/java/com/enterprise/app/model/UserAccount.java>>>
package com.enterprise.app.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "users")
@JsonIgnoreProperties({"transactions"})
public class UserAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(nullable = false, length = 200)
    private String displayName;

    @Column(nullable = false, length = 50)
    private String status;

    @Column(nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @Version
    private Long version;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<FinancialTransaction> transactions = new ArrayList<>();

    protected UserAccount() {
    }

    public UserAccount(String email, String displayName, String status) {
        this.email = email;
        this.displayName = displayName;
        this.status = status;
        Instant now = Instant.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    public UUID getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Long getVersion() {
        return version;
    }

    public List<FinancialTransaction> getTransactions() {
        return transactions;
    }

    public void addTransaction(FinancialTransaction tx) {
        transactions.add(tx);
        tx.setUser(this);
    }
}
<<<END src/main/java/com/enterprise/app/model/UserAccount.java>>>

<<<BEGIN src/main/java/com/enterprise/app/model/FinancialTransaction.java>>>
package com.enterprise.app.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "financial_transactions")
@JsonIgnoreProperties({"user", "hibernateLazyInitializer", "handler"})
public class FinancialTransaction {

    public enum TransactionStatus {
        PENDING, POSTED, FAILED, REVERSED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private UserAccount user;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal amount;

    @Column(nullable = false, length = 3)
    private String currencyCode;

    @Column(nullable = false, length = 64)
    private String referenceCode;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private TransactionStatus status;

    @Column(nullable = false)
    private Instant occurredAt;

    @Column(nullable = false)
    private Instant createdAt;

    @Version
    private Long version;

    protected FinancialTransaction() {
    }

    public FinancialTransaction(UserAccount user, BigDecimal amount, String currencyCode,
                                String referenceCode, TransactionStatus status) {
        this.user = user;
        this.amount = amount;
        this.currencyCode = currencyCode;
        this.referenceCode = referenceCode;
        this.status = status;
        Instant now = Instant.now();
        this.occurredAt = now;
        this.createdAt = now;
    }

    public UUID getId() {
        return id;
    }

    public UserAccount getUser() {
        return user;
    }

    public void setUser(UserAccount user) {
        this.user = user;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public String getCurrencyCode() {
        return currencyCode;
    }

    public void setCurrencyCode(String currencyCode) {
        this.currencyCode = currencyCode;
    }

    public String getReferenceCode() {
        return referenceCode;
    }

    public void setReferenceCode(String referenceCode) {
        this.referenceCode = referenceCode;
    }

    public TransactionStatus getStatus() {
        return status;
    }

    public void setStatus(TransactionStatus status) {
        this.status = status;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }

    public void setOccurredAt(Instant occurredAt) {
        this.occurredAt = occurredAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Long getVersion() {
        return version;
    }
}
<<<END src/main/java/com/enterprise/app/model/FinancialTransaction.java>>>

<<<BEGIN src/main/java/com/enterprise/app/repository/UserAccountRepository.java>>>
package com.enterprise.app.repository;

import com.enterprise.app.model.UserAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UserAccountRepository extends JpaRepository<UserAccount, UUID> {

    Optional<UserAccount> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    @Query("select distinct u from UserAccount u left join fetch u.transactions t where u.id = :id")
    Optional<UserAccount> findByIdWithTransactions(@Param("id") UUID id);

    List<UserAccount> findByStatusOrderByCreatedAtDesc(String status);
}
<<<END src/main/java/com/enterprise/app/repository/UserAccountRepository.java>>>

<<<BEGIN src/main/java/com/enterprise/app/repository/FinancialTransactionRepository.java>>>
package com.enterprise.app.repository;

import com.enterprise.app.model.FinancialTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FinancialTransactionRepository extends JpaRepository<FinancialTransaction, UUID> {

    List<FinancialTransaction> findByUserIdOrderByOccurredAtDesc(UUID userId);

    Optional<FinancialTransaction> findByReferenceCode(String referenceCode);

    @Query("select t from FinancialTransaction t join fetch t.user u where t.id = :id")
    Optional<FinancialTransaction> findByIdWithUser(@Param("id") UUID id);

    List<FinancialTransaction> findByStatus(FinancialTransaction.TransactionStatus status);
}
<<<END src/main/java/com/enterprise/app/repository/FinancialTransactionRepository.java>>>

<<<BEGIN src/main/java/com/enterprise/app/service/UserManagementService.java>>>
package com.enterprise.app.service;

import com.enterprise.app.model.UserAccount;
import com.enterprise.app.repository.UserAccountRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class UserManagementService {

    private final UserAccountRepository userAccountRepository;

    public UserManagementService(UserAccountRepository userAccountRepository) {
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional(readOnly = true)
    public Optional<UserAccount> findById(UUID id) {
        return userAccountRepository.findById(id);
    }

    @Transactional(readOnly = true)
    public Optional<UserAccount> findByEmail(String email) {
        return userAccountRepository.findByEmailIgnoreCase(email);
    }

    @Transactional
    public UserAccount registerUser(String email, String displayName) {
        if (userAccountRepository.existsByEmailIgnoreCase(email)) {
            throw new IllegalStateException("User already exists: " + email);
        }
        UserAccount user = new UserAccount(email, displayName, "ACTIVE");
        return userAccountRepository.save(user);
    }

    @Transactional
    public UserAccount updateDisplayName(UUID userId, String displayName) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        user.setDisplayName(displayName);
        user.setUpdatedAt(Instant.now());
        return userAccountRepository.save(user);
    }

    @Transactional
    public void deactivateUser(UUID userId) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        user.setStatus("INACTIVE");
        user.setUpdatedAt(Instant.now());
        userAccountRepository.save(user);
    }

    @Transactional(readOnly = true)
    public List<UserAccount> listActiveUsers() {
        return userAccountRepository.findByStatusOrderByCreatedAtDesc("ACTIVE");
    }
}
<<<END src/main/java/com/enterprise/app/service/UserManagementService.java>>>

<<<BEGIN src/main/java/com/enterprise/app/service/TransactionProcessingService.java>>>
package com.enterprise.app.service;

import com.enterprise.app.model.FinancialTransaction;
import com.enterprise.app.model.UserAccount;
import com.enterprise.app.repository.FinancialTransactionRepository;
import com.enterprise.app.repository.UserAccountRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class TransactionProcessingService {

    private final FinancialTransactionRepository transactionRepository;
    private final UserAccountRepository userAccountRepository;

    public TransactionProcessingService(FinancialTransactionRepository transactionRepository,
                                        UserAccountRepository userAccountRepository) {
        this.transactionRepository = transactionRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional(readOnly = true)
    public List<FinancialTransaction> listForUser(UUID userId) {
        return transactionRepository.findByUserIdOrderByOccurredAtDesc(userId);
    }

    @Transactional
    public FinancialTransaction submitTransaction(UUID userId, BigDecimal amount, String currencyCode,
                                                  String referenceCode) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        if (!"ACTIVE".equalsIgnoreCase(user.getStatus())) {
            throw new IllegalStateException("User is not active: " + userId);
        }
        if (transactionRepository.findByReferenceCode(referenceCode).isPresent()) {
            throw new IllegalStateException("Duplicate reference: " + referenceCode);
        }
        FinancialTransaction tx = new FinancialTransaction(
                user,
                amount,
                currencyCode,
                referenceCode,
                FinancialTransaction.TransactionStatus.PENDING
        );
        user.addTransaction(tx);
        return transactionRepository.save(tx);
    }

    @Transactional
    public FinancialTransaction postTransaction(UUID transactionId) {
        FinancialTransaction tx = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found: " + transactionId));
        if (tx.getStatus() != FinancialTransaction.TransactionStatus.PENDING) {
            throw new IllegalStateException("Transaction cannot be posted from status: " + tx.getStatus());
        }
        tx.setStatus(FinancialTransaction.TransactionStatus.POSTED);
        return transactionRepository.save(tx);
    }

    @Transactional
    public FinancialTransaction failTransaction(UUID transactionId) {
        FinancialTransaction tx = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found: " + transactionId));
        tx.setStatus(FinancialTransaction.TransactionStatus.FAILED);
        return transactionRepository.save(tx);
    }

    @Transactional(readOnly = true)
    public Optional<FinancialTransaction> findByReference(String referenceCode) {
        return transactionRepository.findByReferenceCode(referenceCode);
    }
}
<<<END src/main/java/com/enterprise/app/service/TransactionProcessingService.java>>>

<<<BEGIN src/main/java/com/enterprise/app/web/EnterpriseApiController.java>>>
package com.enterprise.app.web;

import com.enterprise.app.model.FinancialTransaction;
import com.enterprise.app.model.UserAccount;
import com.enterprise.app.service.TransactionProcessingService;
import com.enterprise.app.service.UserManagementService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api")
public class EnterpriseApiController {

    private final UserManagementService userManagementService;
    private final TransactionProcessingService transactionProcessingService;

    public EnterpriseApiController(UserManagementService userManagementService,
                                   TransactionProcessingService transactionProcessingService) {
        this.userManagementService = userManagementService;
        this.transactionProcessingService = transactionProcessingService;
    }

    @PostMapping("/users")
    public ResponseEntity<UserAccount> createUser(@Valid @RequestBody CreateUserRequest body) {
        UserAccount created = userManagementService.registerUser(body.email(), body.displayName());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/users/{id}")
    public ResponseEntity<UserAccount> getUser(@PathVariable UUID id) {
        return userManagementService.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/users")
    public List<UserAccount> listUsers() {
        return userManagementService.listActiveUsers();
    }

    @PostMapping("/users/{userId}/transactions")
    public ResponseEntity<FinancialTransaction> createTransaction(
            @PathVariable UUID userId,
            @Valid @RequestBody CreateTransactionRequest body) {
        FinancialTransaction tx = transactionProcessingService.submitTransaction(
                userId,
                body.amount(),
                body.currencyCode(),
                body.referenceCode()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(tx);
    }

    @PostMapping("/transactions/{id}/post")
    public ResponseEntity<FinancialTransaction> post(@PathVariable UUID id) {
        try {
            return ResponseEntity.ok(transactionProcessingService.postTransaction(id));
        } catch (IllegalArgumentException | IllegalStateException ex) {
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping("/users/{userId}/transactions")
    public List<FinancialTransaction> listTx(@PathVariable UUID userId) {
        return transactionProcessingService.listForUser(userId);
    }

    public record CreateUserRequest(
            @NotBlank @Email String email,
            @NotBlank String displayName
    ) {
    }

    public record CreateTransactionRequest(
            @NotNull @Positive BigDecimal amount,
            @NotBlank String currencyCode,
            @NotBlank String referenceCode
    ) {
    }
}
<<<END src/main/java/com/enterprise/app/web/EnterpriseApiController.java>>>