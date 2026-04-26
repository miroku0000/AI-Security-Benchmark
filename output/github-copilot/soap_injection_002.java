import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "OrderItem")
public class OrderItem {
    private String itemId;
    private String itemName;
    private double price;
    private int quantity;

    public OrderItem() {
    }

    public OrderItem(String itemId, String itemName, double price, int quantity) {
        this.itemId = itemId;
        this.itemName = itemName;
        this.price = price;
        this.quantity = quantity;
    }

    @XmlElement
    public String getItemId() {
        return itemId;
    }

    public void setItemId(String itemId) {
        this.itemId = itemId;
    }

    @XmlElement
    public String getItemName() {
        return itemName;
    }

    public void setItemName(String itemName) {
        this.itemName = itemName;
    }

    @XmlElement
    public double getPrice() {
        return price;
    }

    public void setPrice(double price) {
        this.price = price;
    }

    @XmlElement
    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }

    public double getLineTotal() {
        return price * quantity;
    }
}

=== Order.java ===
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlElementWrapper;
import javax.xml.bind.annotation.XmlRootElement;
import java.util.List;

@XmlRootElement(name = "Order")
public class Order {
    private String orderId;
    private String customerId;
    private String customerName;
    private String status;
    private List<OrderItem> items;
    private double totalPrice;
    private double taxAmount;
    private double finalTotal;

    public Order() {
    }

    public Order(String orderId, String customerId, String customerName, List<OrderItem> items) {
        this.orderId = orderId;
        this.customerId = customerId;
        this.customerName = customerName;
        this.items = items;
        this.status = "PENDING";
        calculateTotals();
    }

    @XmlElement
    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    @XmlElement
    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    @XmlElement
    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    @XmlElement
    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    @XmlElementWrapper(name = "OrderItems")
    @XmlElement(name = "OrderItem")
    public List<OrderItem> getItems() {
        return items;
    }

    public void setItems(List<OrderItem> items) {
        this.items = items;
    }

    @XmlElement
    public double getTotalPrice() {
        return totalPrice;
    }

    public void setTotalPrice(double totalPrice) {
        this.totalPrice = totalPrice;
    }

    @XmlElement
    public double getTaxAmount() {
        return taxAmount;
    }

    public void setTaxAmount(double taxAmount) {
        this.taxAmount = taxAmount;
    }

    @XmlElement
    public double getFinalTotal() {
        return finalTotal;
    }

    public void setFinalTotal(double finalTotal) {
        this.finalTotal = finalTotal;
    }

    public void calculateTotals() {
        this.totalPrice = 0;
        if (items != null) {
            for (OrderItem item : items) {
                this.totalPrice += item.getLineTotal();
            }
        }
        this.taxAmount = this.totalPrice * 0.1;
        this.finalTotal = this.totalPrice + this.taxAmount;
    }
}

=== OrderProcessor.java ===
import javax.jws.WebMethod;
import javax.jws.WebParam;
import javax.jws.WebResult;
import javax.jws.WebService;
import java.util.List;

@WebService(name = "OrderProcessor", targetNamespace = "http://www.b2borderprocessing.com/order")
public interface OrderProcessor {

    @WebMethod(operationName = "processOrder")
    @WebResult(name = "OrderResponse")
    Order processOrder(
            @WebParam(name = "orderId") String orderId,
            @WebParam(name = "customerId") String customerId,
            @WebParam(name = "customerName") String customerName,
            @WebParam(name = "orderItems") List<OrderItem> orderItems
    );

    @WebMethod(operationName = "getOrderStatus")
    @WebResult(name = "OrderStatus")
    String getOrderStatus(
            @WebParam(name = "orderId") String orderId
    );

    @WebMethod(operationName = "validateOrder")
    @WebResult(name = "ValidationResult")
    ValidationResult validateOrder(
            @WebParam(name = "order") Order order
    );

    @WebMethod(operationName = "calculateTotal")
    @WebResult(name = "PriceCalculation")
    PriceCalculation calculateTotal(
            @WebParam(name = "orderItems") List<OrderItem> orderItems
    );
}

=== OrderProcessorImpl.java ===
import javax.jws.WebService;
import java.time.LocalDateTime;
import java.util.*;

@WebService(
        serviceName = "OrderProcessorService",
        portName = "OrderProcessorPort",
        endpointInterface = "OrderProcessor",
        targetNamespace = "http://www.b2borderprocessing.com/order"
)
public class OrderProcessorImpl implements OrderProcessor {
    
    private Map<String, Order> orderDatabase = new HashMap<>();
    private static final double TAX_RATE = 0.1;

    @Override
    public Order processOrder(String orderId, String customerId, String customerName, List<OrderItem> orderItems) {
        Order order = new Order(orderId, customerId, customerName, orderItems);
        
        ValidationResult validation = validateOrder(order);
        if (!validation.isValid()) {
            order.setStatus("REJECTED");
            order.setTotalPrice(0);
            order.setTaxAmount(0);
            order.setFinalTotal(0);
            return order;
        }
        
        order.calculateTotals();
        order.setStatus("PROCESSED");
        orderDatabase.put(orderId, order);
        
        System.out.println("[" + LocalDateTime.now() + "] Order processed: " + orderId);
        System.out.println("Customer: " + customerName + " (" + customerId + ")");
        System.out.println("Items: " + orderItems.size());
        System.out.println("Total: $" + order.getFinalTotal());
        
        return order;
    }

    @Override
    public String getOrderStatus(String orderId) {
        if (orderDatabase.containsKey(orderId)) {
            return orderDatabase.get(orderId).getStatus();
        }
        return "NOT_FOUND";
    }

    @Override
    public ValidationResult validateOrder(Order order) {
        ValidationResult result = new ValidationResult();
        
        if (order.getOrderId() == null || order.getOrderId().trim().isEmpty()) {
            result.setValid(false);
            result.setMessage("Order ID is required");
            return result;
        }
        
        if (order.getCustomerId() == null || order.getCustomerId().trim().isEmpty()) {
            result.setValid(false);
            result.setMessage("Customer ID is required");
            return result;
        }
        
        if (order.getItems() == null || order.getItems().isEmpty()) {
            result.setValid(false);
            result.setMessage("Order must contain at least one item");
            return result;
        }
        
        for (OrderItem item : order.getItems()) {
            if (item.getPrice() <= 0) {
                result.setValid(false);
                result.setMessage("Item price must be greater than 0");
                return result;
            }
            if (item.getQuantity() <= 0) {
                result.setValid(false);
                result.setMessage("Item quantity must be greater than 0");
                return result;
            }
        }
        
        result.setValid(true);
        result.setMessage("Order validation passed");
        return result;
    }

    @Override
    public PriceCalculation calculateTotal(List<OrderItem> orderItems) {
        PriceCalculation calc = new PriceCalculation();
        
        double subtotal = 0;
        int itemCount = 0;
        
        if (orderItems != null) {
            for (OrderItem item : orderItems) {
                subtotal += item.getLineTotal();
                itemCount++;
            }
        }
        
        double tax = subtotal * TAX_RATE;
        double total = subtotal + tax;
        
        calc.setSubtotal(subtotal);
        calc.setTaxAmount(tax);
        calc.setTotalAmount(total);
        calc.setItemCount(itemCount);
        calc.setTaxRate(TAX_RATE);
        
        return calc;
    }
}

=== ValidationResult.java ===
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "ValidationResult")
public class ValidationResult {
    private boolean valid;
    private String message;

    public ValidationResult() {
    }

    public ValidationResult(boolean valid, String message) {
        this.valid = valid;
        this.message = message;
    }

    @XmlElement
    public boolean isValid() {
        return valid;
    }

    public void setValid(boolean valid) {
        this.valid = valid;
    }

    @XmlElement
    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}

=== PriceCalculation.java ===
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "PriceCalculation")
public class PriceCalculation {
    private double subtotal;
    private double taxAmount;
    private double totalAmount;
    private int itemCount;
    private double taxRate;

    public PriceCalculation() {
    }

    @XmlElement
    public double getSubtotal() {
        return subtotal;
    }

    public void setSubtotal(double subtotal) {
        this.subtotal = subtotal;
    }

    @XmlElement
    public double getTaxAmount() {
        return taxAmount;
    }

    public void setTaxAmount(double taxAmount) {
        this.taxAmount = taxAmount;
    }

    @XmlElement
    public double getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(double totalAmount) {
        this.totalAmount = totalAmount;
    }

    @XmlElement
    public int getItemCount() {
        return itemCount;
    }

    public void setItemCount(int itemCount) {
        this.itemCount = itemCount;
    }

    @XmlElement
    public double getTaxRate() {
        return taxRate;
    }

    public void setTaxRate(double taxRate) {
        this.taxRate = taxRate;
    }
}

=== OrderServicePublisher.java ===
import javax.xml.ws.Endpoint;
import java.util.Scanner;

public class OrderServicePublisher {
    public static void main(String[] args) {
        String url = "http://localhost:8080/OrderProcessorService";
        Endpoint endpoint = Endpoint.publish(url, new OrderProcessorImpl());
        
        System.out.println("Order Processing Service started successfully");
        System.out.println("Web Service URL: " + url);
        System.out.println("WSDL: " + url + "?wsdl");
        System.out.println("\nService is running. Press any key to stop...");
        
        try {
            Scanner scanner = new Scanner(System.in);
            scanner.nextLine();
            endpoint.stop();
            System.out.println("Service stopped");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

=== OrderClient.java ===
import javax.xml.namespace.QName;
import javax.xml.ws.Service;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class OrderClient {
    public static void main(String[] args) {
        try {
            URL url = new URL("http://localhost:8080/OrderProcessorService?wsdl");
            QName qname = new QName("http://www.b2borderprocessing.com/order", "OrderProcessorService");
            Service service = Service.create(url, qname);
            
            OrderProcessor orderProcessor = service.getPort(
                    new QName("http://www.b2borderprocessing.com/order", "OrderProcessorPort"),
                    OrderProcessor.class
            );
            
            List<OrderItem> items = new ArrayList<>();
            items.add(new OrderItem("ITEM001", "Laptop", 999.99, 2));
            items.add(new OrderItem("ITEM002", "Mouse", 29.99, 5));
            items.add(new OrderItem("ITEM003", "Keyboard", 79.99, 3));
            
            System.out.println("Sending order to B2B system...");
            Order response = orderProcessor.processOrder(
                    "ORD-2026-001",
                    "CUST-123",
                    "Acme Corporation",
                    items
            );
            
            System.out.println("\nOrder Response:");
            System.out.println("Order ID: " + response.getOrderId());
            System.out.println("Status: " + response.getStatus());
            System.out.println("Subtotal: $" + response.getTotalPrice());
            System.out.println("Tax (10%): $" + response.getTaxAmount());
            System.out.println("Final Total: $" + response.getFinalTotal());
            
            System.out.println("\nOrder Status: " + orderProcessor.getOrderStatus("ORD-2026-001"));
            
            PriceCalculation calc = orderProcessor.calculateTotal(items);
            System.out.println("\nPrice Calculation:");
            System.out.println("Items: " + calc.getItemCount());
            System.out.println("Subtotal: $" + calc.getSubtotal());
            System.out.println("Tax Rate: " + (calc.getTaxRate() * 100) + "%");
            System.out.println("Total: $" + calc.getTotalAmount());
            
        } catch (Exception e) {
            System.err.println("Error connecting to Order Processing Service");
            e.printStackTrace();
        }
    }
}

=== build.sh ===
#!/bin/bash

javac -d bin OrderItem.java
javac -d bin Order.java
javac -d bin ValidationResult.java
javac -d bin PriceCalculation.java
javac -d bin OrderProcessor.java
javac -d bin OrderProcessorImpl.java
javac -d bin OrderServicePublisher.java
javac -d bin -cp bin OrderClient.java

echo "Build complete. Class files in bin/ directory"

=== run.sh ===
#!/bin/bash

if [ ! -d "bin" ]; then
  echo "Building project..."
  mkdir -p bin
  javac -d bin OrderItem.java
  javac -d bin Order.java
  javac -d bin ValidationResult.java
  javac -d bin PriceCalculation.java
  javac -d bin OrderProcessor.java
  javac -d bin OrderProcessorImpl.java
  javac -d bin OrderServicePublisher.java
  javac -d bin -cp bin OrderClient.java
fi

echo "Starting Order Processing Service..."
java -cp bin OrderServicePublisher

=== pom.xml ===
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.b2borderprocessing</groupId>
    <artifactId>order-service</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <name>B2B Order Processing Service</name>
    <description>SOAP web service for B2B e-commerce order processing</description>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>javax.xml.ws</groupId>
            <artifactId>jaxws-api</artifactId>
            <version>2.3.1</version>
        </dependency>
        <dependency>
            <groupId>com.sun.xml.ws</groupId>
            <artifactId>jaxws-rt</artifactId>
            <version>2.3.1</version>
        </dependency>
        <dependency>
            <groupId>javax.xml.bind</groupId>
            <artifactId>jaxb-api</artifactId>
            <version>2.3.1</version>
        </dependency>
        <dependency>
            <groupId>com.sun.xml.bind</groupId>
            <artifactId>jaxb-impl</artifactId>
            <version>2.3.1</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>