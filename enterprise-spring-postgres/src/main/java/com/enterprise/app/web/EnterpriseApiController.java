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
