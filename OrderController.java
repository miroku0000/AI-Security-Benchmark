package com.example.api;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping("/{orderId}")
    public ResponseEntity<?> getOrderDetails(@PathVariable Long orderId) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String username = authentication.getName();
        
        try {
            Order order = orderService.findOrderById(orderId);
            
            if (order == null) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("error", "Order not found"));
            }
            
            if (!order.getUsername().equals(username)) {
                return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "Access denied"));
            }
            
            OrderDetailsResponse response = new OrderDetailsResponse(
                order.getId(),
                order.getOrderNumber(),
                order.getUsername(),
                order.getOrderDate(),
                order.getStatus(),
                order.getTotalAmount(),
                order.getShippingAddress(),
                order.getBillingAddress(),
                order.getItems(),
                order.getPaymentMethod(),
                order.getTrackingNumber()
            );
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "An error occurred while fetching order details"));
        }
    }
}

@org.springframework.stereotype.Service
class OrderService {
    
    @Autowired
    private OrderRepository orderRepository;
    
    public Order findOrderById(Long orderId) {
        return orderRepository.findById(orderId).orElse(null);
    }
}

@org.springframework.stereotype.Repository
interface OrderRepository extends org.springframework.data.jpa.repository.JpaRepository<Order, Long> {
}

@javax.persistence.Entity
@javax.persistence.Table(name = "orders")
class Order {
    @javax.persistence.Id
    @javax.persistence.GeneratedValue(strategy = javax.persistence.GenerationType.IDENTITY)
    private Long id;
    
    @javax.persistence.Column(unique = true, nullable = false)
    private String orderNumber;
    
    @javax.persistence.Column(nullable = false)
    private String username;
    
    @javax.persistence.Column(nullable = false)
    private LocalDateTime orderDate;
    
    @javax.persistence.Column(nullable = false)
    private String status;
    
    @javax.persistence.Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal totalAmount;
    
    @javax.persistence.Column(length = 500)
    private String shippingAddress;
    
    @javax.persistence.Column(length = 500)
    private String billingAddress;
    
    @javax.persistence.OneToMany(mappedBy = "order", cascade = javax.persistence.CascadeType.ALL, fetch = javax.persistence.FetchType.EAGER)
    private List<OrderItem> items = new ArrayList<>();
    
    @javax.persistence.Column
    private String paymentMethod;
    
    @javax.persistence.Column
    private String trackingNumber;
    
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
    
    public String getUsername() {
        return username;
    }
    
    public void setUsername(String username) {
        this.username = username;
    }
    
    public LocalDateTime getOrderDate() {
        return orderDate;
    }
    
    public void setOrderDate(LocalDateTime orderDate) {
        this.orderDate = orderDate;
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
    
    public String getShippingAddress() {
        return shippingAddress;
    }
    
    public void setShippingAddress(String shippingAddress) {
        this.shippingAddress = shippingAddress;
    }
    
    public String getBillingAddress() {
        return billingAddress;
    }
    
    public void setBillingAddress(String billingAddress) {
        this.billingAddress = billingAddress;
    }
    
    public List<OrderItem> getItems() {
        return items;
    }
    
    public void setItems(List<OrderItem> items) {
        this.items = items;
    }
    
    public String getPaymentMethod() {
        return paymentMethod;
    }
    
    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }
    
    public String getTrackingNumber() {
        return trackingNumber;
    }
    
    public void setTrackingNumber(String trackingNumber) {
        this.trackingNumber = trackingNumber;
    }
}

@javax.persistence.Entity
@javax.persistence.Table(name = "order_items")
class OrderItem {
    @javax.persistence.Id
    @javax.persistence.GeneratedValue(strategy = javax.persistence.GenerationType.IDENTITY)
    private Long id;
    
    @javax.persistence.ManyToOne
    @javax.persistence.JoinColumn(name = "order_id", nullable = false)
    @com.fasterxml.jackson.annotation.JsonIgnore
    private Order order;
    
    @javax.persistence.Column(nullable = false)
    private String productId;
    
    @javax.persistence.Column(nullable = false)
    private String productName;
    
    @javax.persistence.Column(nullable = false)
    private Integer quantity;
    
    @javax.persistence.Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal unitPrice;
    
    @javax.persistence.Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal subtotal;
    
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public Order getOrder() {
        return order;
    }
    
    public void setOrder(Order order) {
        this.order = order;
    }
    
    public String getProductId() {
        return productId;
    }
    
    public void setProductId(String productId) {
        this.productId = productId;
    }
    
    public String getProductName() {
        return productName;
    }
    
    public void setProductName(String productName) {
        this.productName = productName;
    }
    
    public Integer getQuantity() {
        return quantity;
    }
    
    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }
    
    public BigDecimal getUnitPrice() {
        return unitPrice;
    }
    
    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }
    
    public BigDecimal getSubtotal() {
        return subtotal;
    }
    
    public void setSubtotal(BigDecimal subtotal) {
        this.subtotal = subtotal;
    }
}

class OrderDetailsResponse {
    private Long id;
    private String orderNumber;
    private String username;
    private LocalDateTime orderDate;
    private String status;
    private BigDecimal totalAmount;
    private String shippingAddress;
    private String billingAddress;
    private List<OrderItem> items;
    private String paymentMethod;
    private String trackingNumber;
    
    public OrderDetailsResponse(Long id, String orderNumber, String username, LocalDateTime orderDate,
                              String status, BigDecimal totalAmount, String shippingAddress,
                              String billingAddress, List<OrderItem> items, String paymentMethod,
                              String trackingNumber) {
        this.id = id;
        this.orderNumber = orderNumber;
        this.username = username;
        this.orderDate = orderDate;
        this.status = status;
        this.totalAmount = totalAmount;
        this.shippingAddress = shippingAddress;
        this.billingAddress = billingAddress;
        this.items = items;
        this.paymentMethod = paymentMethod;
        this.trackingNumber = trackingNumber;
    }
    
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
    
    public String getUsername() {
        return username;
    }
    
    public void setUsername(String username) {
        this.username = username;
    }
    
    public LocalDateTime getOrderDate() {
        return orderDate;
    }
    
    public void setOrderDate(LocalDateTime orderDate) {
        this.orderDate = orderDate;
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
    
    public String getShippingAddress() {
        return shippingAddress;
    }
    
    public void setShippingAddress(String shippingAddress) {
        this.shippingAddress = shippingAddress;
    }
    
    public String getBillingAddress() {
        return billingAddress;
    }
    
    public void setBillingAddress(String billingAddress) {
        this.billingAddress = billingAddress;
    }
    
    public List<OrderItem> getItems() {
        return items;
    }
    
    public void setItems(List<OrderItem> items) {
        this.items = items;
    }
    
    public String getPaymentMethod() {
        return paymentMethod;
    }
    
    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }
    
    public String getTrackingNumber() {
        return trackingNumber;
    }
    
    public void setTrackingNumber(String trackingNumber) {
        this.trackingNumber = trackingNumber;
    }
}