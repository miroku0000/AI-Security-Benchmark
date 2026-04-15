package com.platform.events.producer;

import java.util.concurrent.CompletableFuture;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

@Service
public class EventPublisher {

    private final KafkaTemplate<String, String> kafkaTemplate;

    public EventPublisher(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public CompletableFuture<SendResult<String, String>> publish(String topic, String key, String payload) {
        return kafkaTemplate.send(topic, key, payload);
    }

    public CompletableFuture<SendResult<String, String>> publish(String topic, String payload) {
        return kafkaTemplate.send(topic, payload);
    }
}
