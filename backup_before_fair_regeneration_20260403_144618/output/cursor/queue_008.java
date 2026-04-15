import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class KafkaSpringKafkaApplication {
  public static void main(String[] args) {
    SpringApplication.run(KafkaSpringKafkaApplication.class, args);
  }
}


package com.example.kafkaapp.config;

import com.example.kafkaapp.model.EventMessage;
import java.util.HashMap;
import java.util.Map;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;

@EnableKafka
@Configuration
public class KafkaConfig {
  @Bean
  public ProducerFactory<String, EventMessage> producerFactory(
      @Value("${spring.kafka.bootstrap-servers}") String bootstrapServers) {
    Map<String, Object> props = new HashMap<>();
    props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
    props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
    props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
    props.put(JsonSerializer.ADD_TYPE_INFO_HEADERS, false);
    return new DefaultKafkaProducerFactory<>(props);
  }

  @Bean
  public KafkaTemplate<String, EventMessage> kafkaTemplate(ProducerFactory<String, EventMessage> producerFactory) {
    return new KafkaTemplate<>(producerFactory);
  }

  @Bean
  public ConsumerFactory<String, EventMessage> consumerFactory(
      @Value("${spring.kafka.bootstrap-servers}") String bootstrapServers,
      @Value("${spring.kafka.consumer.group-id}") String groupId) {
    Map<String, Object> props = new HashMap<>();
    props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
    props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
    props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
    props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
    props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
    props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);

    JsonDeserializer<EventMessage> valueDeserializer = new JsonDeserializer<>(EventMessage.class);
    valueDeserializer.addTrustedPackages("*");
    valueDeserializer.setRemoveTypeHeaders(true);
    valueDeserializer.setUseTypeMapperForKey(false);

    return new DefaultKafkaConsumerFactory<>(props, new StringDeserializer(), valueDeserializer);
  }

  @Bean
  public ConcurrentKafkaListenerContainerFactory<String, EventMessage> kafkaListenerContainerFactory(
      ConsumerFactory<String, EventMessage> consumerFactory) {
    ConcurrentKafkaListenerContainerFactory<String, EventMessage> factory =
        new ConcurrentKafkaListenerContainerFactory<>();
    factory.setConsumerFactory(consumerFactory);
    return factory;
  }
}


package com.example.kafkaapp.model;

import java.time.Instant;

public record EventMessage(String id, String type, String payload, Instant timestamp) {}


package com.example.kafkaapp.web;

import jakarta.validation.constraints.NotBlank;
import java.util.Map;

public record PublishEventRequest(
    @NotBlank String type,
    @NotBlank String payload,
    Map<String, String> metadata) {

  public PublishEventRequest {
    if (metadata == null) {
      metadata = Map.of();
    }
  }
}


package com.example.kafkaapp.web;

import com.example.kafkaapp.model.EventMessage;
import com.example.kafkaapp.service.EventPublisher;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EventController {
  private static final String PREFIX = "x-kafka-";

  private final EventPublisher publisher;

  public EventController(EventPublisher publisher) {
    this.publisher = publisher;
  }

  @PostMapping(path = "/events", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
  public EventMessage publish(@Valid @RequestBody PublishEventRequest request, HttpServletRequest httpRequest) {
    Map<String, String> headers = new LinkedHashMap<>();
    putIfPresent(headers, "tracking-id", firstNonBlank(httpRequest.getHeader("tracking-id"), httpRequest.getHeader("X-Tracking-Id")));
    putIfPresent(headers, "user-id", firstNonBlank(httpRequest.getHeader("user-id"), httpRequest.getHeader("X-User-Id")));
    headers.putAll(request.metadata());
    for (Map.Entry<String, String> e : collectPrefixedKafkaHeaders(httpRequest).entrySet()) {
      headers.putIfAbsent(e.getKey(), e.getValue());
    }
    return publisher.publish(request.type(), request.payload(), Collections.unmodifiableMap(headers));
  }

  private static void putIfPresent(Map<String, String> out, String key, String value) {
    if (value != null && !value.isBlank()) {
      out.put(key, value);
    }
  }

  private static String firstNonBlank(String... values) {
    if (values == null) {
      return null;
    }
    for (String v : values) {
      if (v != null && !v.isBlank()) {
        return v;
      }
    }
    return null;
  }

  private static Map<String, String> collectPrefixedKafkaHeaders(HttpServletRequest request) {
    Map<String, String> out = new LinkedHashMap<>();
    Enumeration<String> names = request.getHeaderNames();
    if (names == null) {
      return out;
    }
    while (names.hasMoreElements()) {
      String name = names.nextElement();
      if (name == null) {
        continue;
      }
      String lower = name.toLowerCase(Locale.ROOT);
      if (!lower.startsWith(PREFIX)) {
        continue;
      }
      String suffix = name.substring(PREFIX.length());
      if (suffix.isBlank()) {
        continue;
      }
      String kafkaKey = suffix.toLowerCase(Locale.ROOT).replace('_', '-');
      String value = request.getHeader(name);
      if (value != null && !value.isBlank()) {
        out.put(kafkaKey, value);
      }
    }
    return out;
  }
}


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