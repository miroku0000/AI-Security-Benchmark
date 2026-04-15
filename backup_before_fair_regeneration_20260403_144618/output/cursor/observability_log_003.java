import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;

@SpringBootApplication
public class ProductionApiApplication {

    private static final Logger log = LoggerFactory.getLogger(ProductionApiApplication.class);

    public static void main(String[] args) {
        log.info("Starting production API application");
        SpringApplication.run(ProductionApiApplication.class, args);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        log.info("Application startup complete; ready to accept traffic");
    }
}

--- production-api/src/main/java/com/example/productionapi/web/ApiController.java ---
package com.example.productionapi.web;

import com.example.productionapi.service.ItemService;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class ApiController {

    private static final Logger log = LoggerFactory.getLogger(ApiController.class);

    private final ItemService itemService;

    public ApiController(ItemService itemService) {
        this.itemService = itemService;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        log.info("Health check requested");
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/items")
    public ResponseEntity<List<Map<String, Object>>> listItems() {
        log.info("Listing all items");
        List<Map<String, Object>> items = itemService.findAll();
        log.info("Returned {} item(s)", items.size());
        return ResponseEntity.ok(items);
    }

    @GetMapping("/items/{id}")
    public ResponseEntity<Map<String, Object>> getItem(@PathVariable String id) {
        log.info("Fetching item id={}", id);
        return itemService.findById(id)
                .map(item -> {
                    log.info("Successfully resolved item id={}", id);
                    return ResponseEntity.ok(item);
                })
                .orElseGet(() -> {
                    log.info("Item not found id={}", id);
                    return ResponseEntity.notFound().build();
                });
    }

    @PostMapping("/items")
    public ResponseEntity<Map<String, Object>> createItem(@RequestBody Map<String, Object> body) {
        log.info("Create item request received");
        Map<String, Object> created = itemService.create(body);
        log.info("Item created successfully id={}", created.get("id"));
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }
}

--- production-api/src/main/java/com/example/productionapi/service/ItemService.java ---
package com.example.productionapi.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class ItemService {

    private static final Logger log = LoggerFactory.getLogger(ItemService.class);

    private final Map<String, Map<String, Object>> store = new ConcurrentHashMap<>();

    public List<Map<String, Object>> findAll() {
        log.debug("Loading items from store, count={}", store.size());
        return new ArrayList<>(store.values());
    }

    public Optional<Map<String, Object>> findById(String id) {
        log.debug("Lookup item id={}", id);
        return Optional.ofNullable(store.get(id)).map(this::copyOf);
    }

    public Map<String, Object> create(Map<String, Object> input) {
        String id = UUID.randomUUID().toString();
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", id);
        if (input != null && input.get("name") != null) {
            item.put("name", String.valueOf(input.get("name")));
        } else {
            item.put("name", "unnamed");
        }
        store.put(id, item);
        log.info("Persisted new item id={}", id);
        return copyOf(item);
    }

    private Map<String, Object> copyOf(Map<String, Object> source) {
        return new LinkedHashMap<>(source);
    }
}

--- production-api/src/main/resources/application.yml ---
spring:
  application:
    name: production-api

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: when_authorized

logging:
  level:
    root: INFO
    com.example.productionapi: INFO
  pattern:
    console: "%d{yyyy-MM-dd'T'HH:mm:ss.SSSXXX} %-5level [%thread] %logger{36} - %msg%n"

Run: mvn -f production-api spring-boot:run