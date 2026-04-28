package com.example.orders;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
public class OrderApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderApplication.class, args);
    }
}

@RestController
@RequestMapping("/orders")
class OrderController {
    private final OrderService orderService;

    OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{orderId}")
    OrderDetailsResponse getOrderById(@PathVariable String orderId) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ResponseStatusException(
                HttpStatus.UNAUTHORIZED,
                "Authenticated user not found in security context"
            );
        }

        return orderService.getOrderById(orderId, authentication.getName());
    }
}

@Service
class OrderService {
    private final Map<String, Order> orders = new ConcurrentHashMap<>();

    OrderService() {
        orders.put(
            "ORD-1001",
            new Order(
                "ORD-1001",
                "CUST-42",
                "PROCESSING",
                new BigDecimal("249.97"),
                "USD",
                Instant.parse("2026-04-22T18:15:30Z"),
                List.of(
                    new OrderItem("SKU-100", "Mechanical Keyboard", 1, new BigDecimal("129.99")),
                    new OrderItem("SKU-200", "Wireless Mouse", 1, new BigDecimal("79.99")),
                    new OrderItem("SKU-300", "Mouse Pad", 1, new BigDecimal("39.99"))
                )
            )
        );
    }

    OrderDetailsResponse getOrderById(String orderId, String authenticatedUser) {
        Order order = orders.get(orderId);
        if (order == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found: " + orderId);
        }

        return new OrderDetailsResponse(
            order.id(),
            order.customerId(),
            authenticatedUser,
            order.status(),
            order.totalAmount(),
            order.currency(),
            order.items().stream()
                .map(item -> new OrderItemResponse(item.sku(), item.name(), item.quantity(), item.unitPrice()))
                .toList(),
            order.createdAt()
        );
    }
}

record Order(
    String id,
    String customerId,
    String status,
    BigDecimal totalAmount,
    String currency,
    Instant createdAt,
    List<OrderItem> items
) {
}

record OrderItem(
    String sku,
    String name,
    int quantity,
    BigDecimal unitPrice
) {
}

record OrderDetailsResponse(
    String orderId,
    String customerId,
    String requestedBy,
    String status,
    BigDecimal totalAmount,
    String currency,
    List<OrderItemResponse> items,
    Instant createdAt
) {
}

record OrderItemResponse(
    String sku,
    String name,
    int quantity,
    BigDecimal unitPrice
) {
}