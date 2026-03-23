package com.example.order;

import java.math.BigDecimal;

public record OrderLineItem(String sku, String description, int quantity, BigDecimal unitPrice) {
}
