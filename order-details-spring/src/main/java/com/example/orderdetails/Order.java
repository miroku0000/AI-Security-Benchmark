package com.example.orderdetails;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;

@Entity
@Table(name = "orders")
public class Order {

    @Id
    private String id;

    @Column(nullable = false)
    private String customerId;

    @Column(nullable = false)
    private BigDecimal total;

    protected Order() {
    }

    public Order(String id, String customerId, BigDecimal total) {
        this.id = id;
        this.customerId = customerId;
        this.total = total;
    }

    public String getId() {
        return id;
    }

    public String getCustomerId() {
        return customerId;
    }

    public BigDecimal getTotal() {
        return total;
    }
}
