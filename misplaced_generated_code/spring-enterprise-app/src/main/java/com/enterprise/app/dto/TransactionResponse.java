package com.enterprise.app.dto;

import com.enterprise.app.model.BusinessTransaction;

import java.math.BigDecimal;
import java.time.Instant;

public record TransactionResponse(
        Long id,
        Long userId,
        BigDecimal amount,
        String currency,
        String status,
        String reference,
        String description,
        Instant createdAt) {

    public static TransactionResponse from(BusinessTransaction t) {
        return new TransactionResponse(
                t.getId(),
                t.getUser().getId(),
                t.getAmount(),
                t.getCurrency(),
                t.getStatus().name(),
                t.getReference(),
                t.getDescription(),
                t.getCreatedAt());
    }
}
