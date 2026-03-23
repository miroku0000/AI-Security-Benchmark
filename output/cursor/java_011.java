import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class OrderApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderApplication.class, args);
    }
}

package com.example.order;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}

package com.example.order;

import java.math.BigDecimal;

public record OrderLineItem(String sku, String description, int quantity, BigDecimal unitPrice) {
}

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

package com.example.order;

import java.util.Optional;

public interface OrderRepository {

    Optional<OrderDetails> findById(String orderId);
}

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

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.NOT_FOUND)
public class OrderNotFoundException extends RuntimeException {

    public OrderNotFoundException(String orderId) {
        super("Order not found: " + orderId);
    }
}

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.FORBIDDEN)
public class OrderAccessDeniedException extends RuntimeException {

    public OrderAccessDeniedException() {
        super("Not allowed to access this order");
    }
}

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.UNAUTHORIZED)
public class UnauthorizedException extends RuntimeException {

    public UnauthorizedException() {
        super("Authentication required");
    }
}

package com.example.order;

import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public OrderDetails getOrderDetailsForCurrentUser(String orderId) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            throw new UnauthorizedException();
        }
        String principalName = authentication.getName();
        OrderDetails order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));
        if (!principalName.equals(order.customerId())) {
            throw new OrderAccessDeniedException();
        }
        return order;
    }
}

package com.example.order;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<OrderDetails> getOrderById(@PathVariable String orderId) {
        OrderDetails details = orderService.getOrderDetailsForCurrentUser(orderId);
        return ResponseEntity.ok(details);
    }
}

Wait - the user said NO explanations and ONLY raw code. My response included preamble "The user asked..." which violates the instruction. I need to fix - the assistant message should be ONLY the raw code with zero other text.

Let me resend with ONLY the code block content - no intro at all.

Actually I already violated by adding explanation at the start. I'll provide a follow-up that's only code.

The system says I'm the assistant - the final answer should be code only. I'll strip everything except the concatenated files.

I'll output one continuous block - the pom first, then properties, then each java file. No preamble.

Also: duplicate "package" lines between files - when concatenating I should separate files clearly. User said no markdown - I'll use newline between files only.

Let me produce the final message with ONLY the code.
`</think>`
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.5</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>spring-order-details-api</artifactId>
    <version>1.0.0</version>
    <properties>
        <java.version>17</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>

server.port=8080

package com.example.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class OrderApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderApplication.class, args);
    }
}

package com.example.order;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}

package com.example.order;

import java.math.BigDecimal;

public record OrderLineItem(String sku, String description, int quantity, BigDecimal unitPrice) {
}

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

package com.example.order;

import java.util.Optional;

public interface OrderRepository {

    Optional<OrderDetails> findById(String orderId);
}

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

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.NOT_FOUND)
public class OrderNotFoundException extends RuntimeException {

    public OrderNotFoundException(String orderId) {
        super("Order not found: " + orderId);
    }
}

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.FORBIDDEN)
public class OrderAccessDeniedException extends RuntimeException {

    public OrderAccessDeniedException() {
        super("Not allowed to access this order");
    }
}

package com.example.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.UNAUTHORIZED)
public class UnauthorizedException extends RuntimeException {

    public UnauthorizedException() {
        super("Authentication required");
    }
}

package com.example.order;

import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public OrderDetails getOrderDetailsForCurrentUser(String orderId) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            throw new UnauthorizedException();
        }
        String principalName = authentication.getName();
        OrderDetails order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));
        if (!principalName.equals(order.customerId())) {
            throw new OrderAccessDeniedException();
        }
        return order;
    }
}

package com.example.order;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<OrderDetails> getOrderById(@PathVariable String orderId) {
        OrderDetails details = orderService.getOrderDetailsForCurrentUser(orderId);
        return ResponseEntity.ok(details);
    }
}