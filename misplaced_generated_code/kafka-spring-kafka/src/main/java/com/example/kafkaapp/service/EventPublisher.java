package com.example.kafkaapp.service;

import com.example.kafkaapp.model.EventMessage;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class EventPublisher {
  private final KafkaTemplate<String, EventMessage> kafkaTemplate;
  private final String topic;

  public EventPublisher(
      KafkaTemplate<String, EventMessage> kafkaTemplate, @Value("${app.kafka.topic}") String topic) {
    this.kafkaTemplate = kafkaTemplate;
    this.topic = topic;
  }

  public EventMessage publish(String type, String payload, Map<String, String> headers) {
    EventMessage msg = new EventMessage(UUID.randomUUID().toString(), type, payload, Instant.now());
    ProducerRecord<String, EventMessage> record = new ProducerRecord<>(topic, msg.id(), msg);
    headers.forEach(
        (key, value) -> {
          if (key != null && !key.isBlank() && value != null) {
            record.headers().add(key, value.getBytes(StandardCharsets.UTF_8));
          }
        });
    kafkaTemplate.send(record);
    return msg;
  }
}
