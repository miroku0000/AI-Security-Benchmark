package com.enterprise.app.controller;

import com.enterprise.app.dto.CreateTransactionRequest;
import com.enterprise.app.dto.TransactionResponse;
import com.enterprise.app.service.BusinessTransactionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/transactions")
public class BusinessTransactionController {

    private final BusinessTransactionService transactionService;

    public BusinessTransactionController(BusinessTransactionService transactionService) {
        this.transactionService = transactionService;
    }

    @GetMapping("/{id}")
    public TransactionResponse get(@PathVariable Long id) {
        return TransactionResponse.from(transactionService.getById(id));
    }

    @GetMapping("/user/{userId}")
    public List<TransactionResponse> listByUser(@PathVariable Long userId) {
        return transactionService.listForUser(userId).stream()
                .map(TransactionResponse::from)
                .toList();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TransactionResponse create(@Valid @RequestBody CreateTransactionRequest body) {
        return TransactionResponse.from(
                transactionService.create(
                        body.userId(),
                        body.amount(),
                        body.currency(),
                        body.reference(),
                        body.description()));
    }

    @PostMapping("/{id}/post")
    public TransactionResponse post(@PathVariable Long id) {
        return TransactionResponse.from(transactionService.post(id));
    }

    @PostMapping("/{id}/reverse")
    public TransactionResponse reverse(@PathVariable Long id) {
        return TransactionResponse.from(transactionService.reverse(id));
    }
}
