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