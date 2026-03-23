package com.example.orderdetails;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public OrderDetailsDto getOrderForCurrentUser(String orderId) {
        String username = SecurityContextHolder.getContext().getAuthentication().getName();
        return orderRepository.findByIdAndCustomerId(orderId, username)
                .map(o -> new OrderDetailsDto(o.getId(), o.getCustomerId(), o.getTotal()))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found"));
    }
}
