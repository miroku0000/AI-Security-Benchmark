package com.example.orderdetails;

import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class SampleDataLoader implements CommandLineRunner {

    private final OrderRepository orderRepository;

    public SampleDataLoader(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @Override
    public void run(String... args) {
        orderRepository.save(new Order("ord-1001", "alice", new BigDecimal("149.99")));
        orderRepository.save(new Order("ord-1002", "bob", new BigDecimal("29.50")));
    }
}
