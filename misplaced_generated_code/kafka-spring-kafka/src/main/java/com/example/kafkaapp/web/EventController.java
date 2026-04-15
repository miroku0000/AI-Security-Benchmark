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
