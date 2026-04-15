package com.enterprise.app.controller;

import com.enterprise.app.dto.CreateTransactionRequest;
import com.enterprise.app.dto.TransactionResponse;
import com.enterprise.app.entity.AccountTransactionEntity;
import com.enterprise.app.service.TransactionService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users/{userId}/transactions")
public class TransactionController {
  private final TransactionService transactionService;

  public TransactionController(TransactionService transactionService) {
    this.transactionService = transactionService;
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public TransactionResponse create(@PathVariable UUID userId, @Valid @RequestBody CreateTransactionRequest req) {
    return toResponse(transactionService.create(userId, req));
  }

  @GetMapping
  public List<TransactionResponse> list(@PathVariable UUID userId) {
    return transactionService.listForUser(userId).stream().map(TransactionController::toResponse).toList();
  }

  static TransactionResponse toResponse(AccountTransactionEntity tx) {
    TransactionResponse r = new TransactionResponse();
    r.setId(tx.getId());
    r.setUserId(tx.getUserId());
    r.setAmount(tx.getAmount());
    r.setCurrency(tx.getCurrency());
    r.setType(tx.getType());
    r.setReference(tx.getReference());
    r.setCreatedAt(tx.getCreatedAt());
    return r;
  }
}

