package com.example.webhook;

public record WebhookResponse(Integer statusCode, String body, String error) {
}
