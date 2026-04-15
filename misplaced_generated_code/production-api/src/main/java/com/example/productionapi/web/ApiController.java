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
