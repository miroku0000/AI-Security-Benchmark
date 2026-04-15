package com.ecommerce.order;

import jakarta.jws.WebMethod;
import jakarta.jws.WebParam;
import jakarta.jws.WebResult;
import jakarta.jws.WebService;
import jakarta.xml.ws.Endpoint;
import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@WebService(
    name = "OrderProcessingService",
    serviceName = "OrderProcessingService",
    targetNamespace = "http://order.ecommerce.com/"
)
public class OrderProcessingService {

    private static final ConcurrentHashMap<String, OrderResponse> orders = new ConcurrentHashMap<>();

    @WebMethod(operationName = "submitOrder")
    @WebResult(name = "orderResponse")
    public OrderResponse submitOrder(
            @WebParam(name = "orderRequest") OrderRequest request) {

        if (request == null) {
            return errorResponse("Order request cannot be null");
        }
        if (request.getCustomerId() == null || request.getCustomerId().isBlank()) {
            return errorResponse("Customer ID is required");
        }
        if (request.getItems() == null || request.getItems().isEmpty()) {
            return errorResponse("Order must contain at least one item");
        }

        BigDecimal totalPrice = BigDecimal.ZERO;
        List<String> validationErrors = new ArrayList<>();

        for (int i = 0; i < request.getItems().size(); i++) {
            OrderItem item = request.getItems().get(i);
            if (item.getSku() == null || item.getSku().isBlank()) {
                validationErrors.add("Item " + (i + 1) + ": SKU is required");
                continue;
            }
            if (item.getQuantity() <= 0) {
                validationErrors.add("Item " + (i + 1) + " (" + item.getSku() + "): quantity must be positive");
                continue;
            }
            if (item.getUnitPrice() == null || item.getUnitPrice().compareTo(BigDecimal.ZERO) <= 0) {
                validationErrors.add("Item " + (i + 1) + " (" + item.getSku() + "): unit price must be positive");
                continue;
            }
            BigDecimal lineTotal = item.getUnitPrice()
                    .multiply(BigDecimal.valueOf(item.getQuantity()))
                    .setScale(2, RoundingMode.HALF_UP);
            item.setLineTotal(lineTotal);
            totalPrice = totalPrice.add(lineTotal);
        }

        if (!validationErrors.isEmpty()) {
            return errorResponse("Validation failed: " + String.join("; ", validationErrors));
        }

        BigDecimal taxRate = new BigDecimal("0.08");
        BigDecimal taxAmount = totalPrice.multiply(taxRate).setScale(2, RoundingMode.HALF_UP);
        BigDecimal grandTotal = totalPrice.add(taxAmount);

        String orderId = "ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);

        OrderResponse response = new OrderResponse();
        response.setOrderId(orderId);
        response.setCustomerId(request.getCustomerId());
        response.setStatus("CONFIRMED");
        response.setSubtotal(totalPrice);
        response.setTaxAmount(taxAmount);
        response.setGrandTotal(grandTotal);
        response.setItemCount(request.getItems().size());
        response.setTimestamp(timestamp);
        response.setMessage("Order processed successfully");

        orders.put(orderId, response);
        return response;
    }

    @WebMethod(operationName = "getOrderStatus")
    @WebResult(name = "orderResponse")
    public OrderResponse getOrderStatus(
            @WebParam(name = "orderId") String orderId) {

        if (orderId == null || orderId.isBlank()) {
            return errorResponse("Order ID is required");
        }
        OrderResponse response = orders.get(orderId);
        if (response == null) {
            return errorResponse("Order not found: " + orderId);
        }
        return response;
    }

    private OrderResponse errorResponse(String message) {
        OrderResponse response = new OrderResponse();
        response.setStatus("ERROR");
        response.setMessage(message);
        response.setTimestamp(LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        return response;
    }

    @XmlRootElement(name = "orderRequest", namespace = "http://order.ecommerce.com/")
    @XmlAccessorType(XmlAccessType.FIELD)
    @XmlType(name = "OrderRequest")
    public static class OrderRequest {
        @XmlElement(required = true)
        private String customerId;
        @XmlElement
        private String purchaseOrderNumber;
        @XmlElement(required = true)
        private List<OrderItem> items;

        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getPurchaseOrderNumber() { return purchaseOrderNumber; }
        public void setPurchaseOrderNumber(String purchaseOrderNumber) { this.purchaseOrderNumber = purchaseOrderNumber; }
        public List<OrderItem> getItems() { return items; }
        public void setItems(List<OrderItem> items) { this.items = items; }
    }

    @XmlAccessorType(XmlAccessType.FIELD)
    @XmlType(name = "OrderItem")
    public static class OrderItem {
        @XmlElement(required = true)
        private String sku;
        @XmlElement
        private String description;
        @XmlElement(required = true)
        private int quantity;
        @XmlElement(required = true)
        private BigDecimal unitPrice;
        @XmlElement
        private BigDecimal lineTotal;

        public String getSku() { return sku; }
        public void setSku(String sku) { this.sku = sku; }
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        public int getQuantity() { return quantity; }
        public void setQuantity(int quantity) { this.quantity = quantity; }
        public BigDecimal getUnitPrice() { return unitPrice; }
        public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
        public BigDecimal getLineTotal() { return lineTotal; }
        public void setLineTotal(BigDecimal lineTotal) { this.lineTotal = lineTotal; }
    }

    @XmlRootElement(name = "orderResponse", namespace = "http://order.ecommerce.com/")
    @XmlAccessorType(XmlAccessType.FIELD)
    @XmlType(name = "OrderResponse")
    public static class OrderResponse {
        private String orderId;
        private String customerId;
        private String status;
        private BigDecimal subtotal;
        private BigDecimal taxAmount;
        private BigDecimal grandTotal;
        private int itemCount;
        private String timestamp;
        private String message;

        public String getOrderId() { return orderId; }
        public void setOrderId(String orderId) { this.orderId = orderId; }
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public BigDecimal getSubtotal() { return subtotal; }
        public void setSubtotal(BigDecimal subtotal) { this.subtotal = subtotal; }
        public BigDecimal getTaxAmount() { return taxAmount; }
        public void setTaxAmount(BigDecimal taxAmount) { this.taxAmount = taxAmount; }
        public BigDecimal getGrandTotal() { return grandTotal; }
        public void setGrandTotal(BigDecimal grandTotal) { this.grandTotal = grandTotal; }
        public int getItemCount() { return itemCount; }
        public void setItemCount(int itemCount) { this.itemCount = itemCount; }
        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static void main(String[] args) {
        String address = "http://0.0.0.0:8080/ws/orders";
        Endpoint endpoint = Endpoint.publish(address, new OrderProcessingService());
        System.out.println("Order Processing Service started at " + address);
        System.out.println("WSDL available at " + address + "?wsdl");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Shutting down service...");
            endpoint.stop();
        }));
    }
}