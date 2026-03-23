package com.example.webhook.web;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.example.webhook.dto.PartnerWebhookRequest;
import com.example.webhook.service.UrlFetchService;
import com.example.webhook.service.UrlFetchService.FetchedContent;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/webhooks/partner")
@Validated
public class PartnerWebhookController {

    private final UrlFetchService urlFetchService;

    public PartnerWebhookController(UrlFetchService urlFetchService) {
        this.urlFetchService = urlFetchService;
    }

    @PostMapping(value = "/fetch", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<byte[]> handlePartnerWebhookJson(
            @Valid @RequestBody PartnerWebhookRequest request,
            @RequestParam(name = "client", defaultValue = "rest") String client) {
        FetchedContent fetched = "http".equalsIgnoreCase(client)
                ? urlFetchService.fetchWithHttpClient(request.getUrl())
                : urlFetchService.fetchWithRestTemplate(request.getUrl());
        return buildResponse(fetched);
    }

    @PostMapping(value = "/fetch-form", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public ResponseEntity<byte[]> handlePartnerWebhookForm(
            @Valid PartnerWebhookRequest request,
            @RequestParam(name = "client", defaultValue = "rest") String client) {
        FetchedContent fetched = "http".equalsIgnoreCase(client)
                ? urlFetchService.fetchWithHttpClient(request.getUrl())
                : urlFetchService.fetchWithRestTemplate(request.getUrl());
        return buildResponse(fetched);
    }

    private static ResponseEntity<byte[]> buildResponse(FetchedContent fetched) {
        HttpHeaders headers = new HttpHeaders();
        headers.add(HttpHeaders.CONTENT_TYPE, fetched.contentType());
        return ResponseEntity.status(fetched.statusCode()).headers(headers).body(fetched.body());
    }
}
