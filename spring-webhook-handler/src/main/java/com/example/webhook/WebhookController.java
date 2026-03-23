package com.example.webhook;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/partner")
public class WebhookController {

    private final UrlFetchService urlFetchService;

    public WebhookController(UrlFetchService urlFetchService) {
        this.urlFetchService = urlFetchService;
    }

    @PostMapping(value = "/webhook", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<WebhookResponse> handleWebhook(@RequestBody WebhookRequest request) {
        if (request == null || request.url() == null || request.url().isBlank()) {
            return ResponseEntity.badRequest().body(new WebhookResponse(null, null, "url is required"));
        }
        try {
            FetchedContent fetched = urlFetchService.fetchUrl(request.url());
            return ResponseEntity.ok(new WebhookResponse(
                    fetched.statusCode(),
                    fetched.body(),
                    null
            ));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(new WebhookResponse(null, null, e.getMessage()));
        }
    }
}
