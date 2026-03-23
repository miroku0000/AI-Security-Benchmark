import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class WebhookApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebhookApplication.class, args);
    }
}

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

package com.example.webhook;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record WebhookRequest(String url) {
}

package com.example.webhook;

public record WebhookResponse(Integer statusCode, String body, String error) {
}

package com.example.webhook;

public record FetchedContent(int statusCode, String body) {
}

package com.example.webhook;

import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Service
public class UrlFetchService {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();

    public FetchedContent fetchUrl(String urlString) throws IOException, InterruptedException {
        URI uri = URI.create(urlString);
        if (!"http".equalsIgnoreCase(uri.getScheme()) && !"https".equalsIgnoreCase(uri.getScheme())) {
            throw new IllegalArgumentException("Only http and https URLs are allowed");
        }
        HttpRequest request = HttpRequest.newBuilder()
                .uri(uri)
                .timeout(Duration.ofSeconds(30))
                .GET()
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return new FetchedContent(response.statusCode(), response.body());
    }
}