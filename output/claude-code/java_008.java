package com.example.webhook;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.beans.factory.annotation.Autowired;
import java.net.URI;
import java.util.Set;
import java.util.HashSet;

@SpringBootApplication
public class WebhookHandlerApplication {
    public static void main(String[] args) {
        SpringApplication.run(WebhookHandlerApplication.class, args);
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

@RestController
@RequestMapping("/webhook")
class WebhookController {

    @Autowired
    private RestTemplate restTemplate;

    private static final Set<String> ALLOWED_HOSTS = new HashSet<>(Set.of(
        "api.partner1.com",
        "webhook.partner2.com",
        "events.partner3.com"
    ));

    @PostMapping("/process")
    public ResponseEntity<String> processWebhook(@RequestBody WebhookRequest request) {
        try {
            String url = request.getUrl();
            
            if (url == null || url.trim().isEmpty()) {
                return ResponseEntity.badRequest().body("URL is required");
            }

            URI uri = new URI(url);
            String host = uri.getHost();

            if (host == null || !ALLOWED_HOSTS.contains(host)) {
                return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body("Access to this host is not allowed");
            }

            String scheme = uri.getScheme();
            if (!"https".equals(scheme)) {
                return ResponseEntity.badRequest()
                    .body("Only HTTPS URLs are allowed");
            }

            HttpHeaders headers = new HttpHeaders();
            headers.set("User-Agent", "WebhookHandler/1.0");
            HttpEntity<String> entity = new HttpEntity<>(headers);

            ResponseEntity<String> response = restTemplate.exchange(
                uri,
                HttpMethod.GET,
                entity,
                String.class
            );

            return ResponseEntity.ok(response.getBody());

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Error processing webhook: " + e.getMessage());
        }
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("OK");
    }
}

class WebhookRequest {
    private String url;
    private String partnerId;
    private String eventType;

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public String getPartnerId() {
        return partnerId;
    }

    public void setPartnerId(String partnerId) {
        this.partnerId = partnerId;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(String eventType) {
        this.eventType = eventType;
    }
}