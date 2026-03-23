package com.example.orderdetails;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface OrderRepository extends JpaRepository<Order, String> {

    Optional<Order> findByIdAndCustomerId(String id, String customerId);
}
