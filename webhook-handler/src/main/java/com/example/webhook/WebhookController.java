package com.example.webhook;

import com.example.webhook.dto.FetchResponse;
import com.example.webhook.dto.WebhookRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClientException;

@RestController
@RequestMapping("/webhook")
public class WebhookController {

    private final WebhookService webhookService;

    public WebhookController(WebhookService webhookService) {
        this.webhookService = webhookService;
    }

    @PostMapping("/partner")
    public ResponseEntity<FetchResponse> handlePartnerWebhook(@Valid @RequestBody WebhookRequest request) {
        FetchResponse result = webhookService.fetchUrl(request.getUrl());
        return ResponseEntity.ok(result);
    }

    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<String> handleFetchFailure(RestClientException ex) {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(ex.getMessage());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<String> handleBadUrl(IllegalArgumentException ex) {
        return ResponseEntity.badRequest().body(ex.getMessage());
    }
}
