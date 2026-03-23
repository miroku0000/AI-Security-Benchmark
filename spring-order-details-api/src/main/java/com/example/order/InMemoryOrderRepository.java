package com.example.order;

import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class InMemoryOrderRepository implements OrderRepository {

    private final Map<String, OrderDetails> orders = new ConcurrentHashMap<>();

    public InMemoryOrderRepository() {
        Instant t = Instant.parse("2024-01-15T12:00:00Z");
        orders.put("ORD-1001", new OrderDetails(
                "ORD-1001",
                "user-1",
                "SHIPPED",
                new BigDecimal("129.99"),
                t,
                List.of(new OrderLineItem("SKU-A", "Widget", 2, new BigDecimal("49.99")))
        ));
        orders.put("ORD-1002", new OrderDetails(
                "ORD-1002",
                "user-2",
                "PROCESSING",
                new BigDecimal("59.50"),
                t,
                List.of(new OrderLineItem("SKU-B", "Gadget", 1, new BigDecimal("59.50")))
        ));
    }

    @Override
    public Optional<OrderDetails> findById(String orderId) {
        return Optional.ofNullable(orders.get(orderId));
    }
}
