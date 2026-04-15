package com.enterprise.app.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public record CreateTransactionRequest(
        @NotNull Long userId,
        @NotNull @DecimalMin("0.0001") BigDecimal amount,
        @NotBlank @Size(max = 8) String currency,
        @NotBlank @Size(max = 64) String reference,
        @Size(max = 512) String description) {
}
