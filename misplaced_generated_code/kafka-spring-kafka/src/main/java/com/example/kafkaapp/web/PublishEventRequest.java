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
