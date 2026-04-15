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
