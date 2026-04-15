package com.platform.events.web;

import java.util.concurrent.ExecutionException;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.platform.events.producer.EventPublisher;

@RestController
@RequestMapping("/api/events")
public class EventController {

    private static final String TOPIC = "platform-events";

    private final EventPublisher eventPublisher;

    public EventController(EventPublisher eventPublisher) {
        this.eventPublisher = eventPublisher;
    }

    @PostMapping
    public ResponseEntity<String> publish(@RequestBody String body) throws ExecutionException, InterruptedException {
        eventPublisher.publish(TOPIC, body).get();
        return ResponseEntity.accepted().body("accepted");
    }
}
