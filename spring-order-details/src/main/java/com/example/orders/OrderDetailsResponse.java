package com.example.orders;

import java.math.BigDecimal;
import java.time.Instant;

public class OrderDetailsResponse {

    private Long id;
    private String orderNumber;
    private String status;
    private BigDecimal totalAmount;
    private Instant placedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getOrderNumber() {
        return orderNumber;
    }

    public void setOrderNumber(String orderNumber) {
        this.orderNumber = orderNumber;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(BigDecimal totalAmount) {
        this.totalAmount = totalAmount;
    }

    public Instant getPlacedAt() {
        return placedAt;
    }

    public void setPlacedAt(Instant placedAt) {
        this.placedAt = placedAt;
    }

    public static OrderDetailsResponse fromEntity(Order order) {
        OrderDetailsResponse r = new OrderDetailsResponse();
        r.setId(order.getId());
        r.setOrderNumber(order.getOrderNumber());
        r.setStatus(order.getStatus());
        r.setTotalAmount(order.getTotalAmount());
        r.setPlacedAt(order.getPlacedAt());
        return r;
    }
}
