package com.example.order;

import java.util.Optional;

public interface OrderRepository {

    Optional<OrderDetails> findById(String orderId);
}
