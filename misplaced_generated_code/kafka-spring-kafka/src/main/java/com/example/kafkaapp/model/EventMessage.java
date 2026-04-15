package com.example.kafkaapp.model;

import java.time.Instant;

public record EventMessage(String id, String type, String payload, Instant timestamp) {}

