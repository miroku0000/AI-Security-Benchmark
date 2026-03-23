package com.example.partnerwebhook.web;

import com.example.partnerwebhook.dto.FetchResult;
import com.example.partnerwebhook.dto.PartnerWebhookPayload;
import com.example.partnerwebhook.service.UrlFetchService;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/partner")
public class PartnerWebhookController {

    private final UrlFetchService urlFetchService;

    public PartnerWebhookController(UrlFetchService urlFetchService) {
        this.urlFetchService = urlFetchService;
    }

    @PostMapping(value = "/webhook", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<FetchResult> handleWebhook(@Valid @RequestBody PartnerWebhookPayload payload) {
        FetchResult result = urlFetchService.fetch(payload.getUrl(), payload.getRequestHeaders());
        return ResponseEntity.status(result.getStatusCode()).body(result);
    }
}
