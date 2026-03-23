package com.example.order;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderDetails(
        String orderId,
        String customerId,
        String status,
        BigDecimal total,
        Instant placedAt,
        List<OrderLineItem> lineItems
) {
}
