package com.example.webhook.controller;

import com.example.webhook.dto.WebhookRequest;
import com.example.webhook.service.UrlFetchService;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/partners")
public class PartnerWebhookController {

    private final UrlFetchService urlFetchService;

    public PartnerWebhookController(UrlFetchService urlFetchService) {
        this.urlFetchService = urlFetchService;
    }

    @PostMapping("/webhook")
    public ResponseEntity<String> handlePartnerWebhook(@Valid @RequestBody WebhookRequest body) {
        ResponseEntity<String> upstream = urlFetchService.fetch(body.getUrl());
        HttpHeaders out = new HttpHeaders();
        upstream.getHeaders().forEach((name, values) -> {
            if (HttpHeaders.CONTENT_TYPE.equalsIgnoreCase(name) && !values.isEmpty()) {
                out.add(HttpHeaders.CONTENT_TYPE, values.get(0));
            }
        });
        return ResponseEntity.status(upstream.getStatusCode()).headers(out).body(upstream.getBody());
    }
}
