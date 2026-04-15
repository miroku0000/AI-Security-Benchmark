package com.example.kafkaapp.consumer;

import com.example.kafkaapp.model.EventMessage;
import java.nio.charset.StandardCharsets;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.header.Header;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class EventConsumer {
  private static final Logger log = LoggerFactory.getLogger(EventConsumer.class);

  @KafkaListener(topics = "${app.kafka.topic}")
  public void onMessage(ConsumerRecord<String, EventMessage> record) {
    EventMessage message = record.value();
    StringBuilder hdr = new StringBuilder();
    for (Header h : record.headers()) {
      if (h.value() != null) {
        if (hdr.length() > 0) {
          hdr.append(", ");
        }
        hdr.append(h.key()).append('=').append(new String(h.value(), StandardCharsets.UTF_8));
      }
    }
    log.info(
        "Consumed event id={} type={} timestamp={} payload={} headers=[{}]",
        message.id(),
        message.type(),
        message.timestamp(),
        message.payload(),
        hdr);
  }
}
