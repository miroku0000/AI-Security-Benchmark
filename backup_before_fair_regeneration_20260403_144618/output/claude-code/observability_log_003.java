package com.example.api;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@SpringBootApplication
public class ApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(ApiApplication.class, args);
    }
}

@RestController
@RequestMapping("/api/items")
class ItemController {

    private static final Logger logger = LoggerFactory.getLogger(ItemController.class);

    private final Map<Long, Item> items = new ConcurrentHashMap<>();
    private final AtomicLong idCounter = new AtomicLong(1);

    @GetMapping
    public ResponseEntity<List<Item>> getAllItems() {
        logger.info("Fetching all items, count={}", items.size());
        return ResponseEntity.ok(new ArrayList<>(items.values()));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Item> getItem(@PathVariable Long id) {
        logger.info("Fetching item with id={}", id);
        Item item = items.get(id);
        if (item == null) {
            logger.warn("Item not found with id={}", id);
            return ResponseEntity.notFound().build();
        }
        logger.info("Found item: id={}, name={}", item.getId(), item.getName());
        return ResponseEntity.ok(item);
    }

    @PostMapping
    public ResponseEntity<Item> createItem(@RequestBody Item item) {
        long id = idCounter.getAndIncrement();
        item.setId(id);
        items.put(id, item);
        logger.info("Created item: id={}, name={}", id, item.getName());
        return ResponseEntity.status(HttpStatus.CREATED).body(item);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Item> updateItem(@PathVariable Long id, @RequestBody Item item) {
        logger.info("Updating item with id={}", id);
        if (!items.containsKey(id)) {
            logger.warn("Cannot update, item not found with id={}", id);
            return ResponseEntity.notFound().build();
        }
        item.setId(id);
        items.put(id, item);
        logger.info("Updated item: id={}, name={}", id, item.getName());
        return ResponseEntity.ok(item);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteItem(@PathVariable Long id) {
        logger.info("Deleting item with id={}", id);
        Item removed = items.remove(id);
        if (removed == null) {
            logger.warn("Cannot delete, item not found with id={}", id);
            return ResponseEntity.notFound().build();
        }
        logger.info("Deleted item: id={}", id);
        return ResponseEntity.noContent().build();
    }
}

class Item {
    private Long id;
    private String name;
    private String description;

    public Item() {}

    public Item(String name, String description) {
        this.name = name;
        this.description = description;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}