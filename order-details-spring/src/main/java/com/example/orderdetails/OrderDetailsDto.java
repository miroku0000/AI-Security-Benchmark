package com.example.orderdetails;

import java.math.BigDecimal;

public record OrderDetailsDto(String orderId, String customerId, BigDecimal total) {
}
