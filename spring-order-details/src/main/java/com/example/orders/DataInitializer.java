package com.example.orders;

import java.math.BigDecimal;
import java.time.Instant;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements ApplicationRunner {

    private final OrderRepository orderRepository;

    public DataInitializer(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @Override
    public void run(ApplicationArguments args) {
        Order o = new Order();
        o.setOwnerUsername("demo");
        o.setOrderNumber("ORD-1001");
        o.setStatus("SHIPPED");
        o.setTotalAmount(new BigDecimal("129.99"));
        o.setPlacedAt(Instant.parse("2025-01-15T12:30:00Z"));
        orderRepository.save(o);
    }
}
