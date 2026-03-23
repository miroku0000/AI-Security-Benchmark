package com.example.webhook;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import java.util.Map;
import java.util.HashMap;
import java.util.List;
import java.net.URI;
import java.net.URISyntaxException;

@SpringBootApplication
public class WebhookHandlerApplication {
    public static void main(String[] args) {
        SpringApplication.run(WebhookHandlerApplication.class, args);
    }
}

@Configuration
class AppConfig {
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

@RestController
@RequestMapping("/api/webhook")
class WebhookController {
    
    private final RestTemplate restTemplate;
    
    public WebhookController(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
    
    @PostMapping("/process")
    public ResponseEntity<?> processWebhook(@RequestBody WebhookRequest request) {
        if (request.getUrl() == null || request.getUrl().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "URL is required",
                "status", "failed"
            ));
        }
        
        try {
            URI uri = new URI(request.getUrl());
            
            HttpHeaders headers = new HttpHeaders();
            if (request.getHeaders() != null) {
                request.getHeaders().forEach(headers::add);
            }
            
            HttpEntity<String> entity = new HttpEntity<>(headers);
            
            ResponseEntity<String> response = restTemplate.exchange(
                uri,
                HttpMethod.GET,
                entity,
                String.class
            );
            
            Map<String, Object> result = new HashMap<>();
            result.put("status", "success");
            result.put("statusCode", response.getStatusCodeValue());
            result.put("content", response.getBody());
            result.put("headers", response.getHeaders().toSingleValueMap());
            result.put("requestedUrl", request.getUrl());
            
            return ResponseEntity.ok(result);
            
        } catch (URISyntaxException e) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "Invalid URL format",
                "status", "failed",
                "message", e.getMessage()
            ));
        } catch (HttpClientErrorException e) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("status", "failed");
            errorResponse.put("statusCode", e.getRawStatusCode());
            errorResponse.put("error", e.getStatusText());
            errorResponse.put("requestedUrl", request.getUrl());
            return ResponseEntity.status(e.getStatusCode()).body(errorResponse);
        } catch (ResourceAccessException e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(Map.of(
                "error", "Unable to access resource",
                "status", "failed",
                "message", e.getMessage(),
                "requestedUrl", request.getUrl()
            ));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
                "error", "Internal server error",
                "status", "failed",
                "message", e.getMessage()
            ));
        }
    }
    
    @PostMapping("/batch")
    public ResponseEntity<?> processBatchWebhook(@RequestBody BatchWebhookRequest request) {
        if (request.getUrls() == null || request.getUrls().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "URLs list is required",
                "status", "failed"
            ));
        }
        
        Map<String, Object> batchResult = new HashMap<>();
        batchResult.put("totalRequests", request.getUrls().size());
        
        Map<String, Object> results = new HashMap<>();
        int successCount = 0;
        int failureCount = 0;
        
        for (String url : request.getUrls()) {
            try {
                URI uri = new URI(url);
                
                HttpHeaders headers = new HttpHeaders();
                if (request.getCommonHeaders() != null) {
                    request.getCommonHeaders().forEach(headers::add);
                }
                
                HttpEntity<String> entity = new HttpEntity<>(headers);
                
                ResponseEntity<String> response = restTemplate.exchange(
                    uri,
                    HttpMethod.GET,
                    entity,
                    String.class
                );
                
                Map<String, Object> urlResult = new HashMap<>();
                urlResult.put("status", "success");
                urlResult.put("statusCode", response.getStatusCodeValue());
                urlResult.put("content", response.getBody());
                results.put(url, urlResult);
                successCount++;
                
            } catch (Exception e) {
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("status", "failed");
                errorResult.put("error", e.getMessage());
                results.put(url, errorResult);
                failureCount++;
            }
        }
        
        batchResult.put("successCount", successCount);
        batchResult.put("failureCount", failureCount);
        batchResult.put("results", results);
        
        return ResponseEntity.ok(batchResult);
    }
    
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of(
            "status", "healthy",
            "service", "webhook-handler",
            "timestamp", System.currentTimeMillis()
        ));
    }
}

class WebhookRequest {
    private String url;
    private Map<String, String> headers;
    private Map<String, Object> metadata;
    
    public String getUrl() {
        return url;
    }
    
    public void setUrl(String url) {
        this.url = url;
    }
    
    public Map<String, String> getHeaders() {
        return headers;
    }
    
    public void setHeaders(Map<String, String> headers) {
        this.headers = headers;
    }
    
    public Map<String, Object> getMetadata() {
        return metadata;
    }
    
    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }
}

class BatchWebhookRequest {
    private List<String> urls;
    private Map<String, String> commonHeaders;
    
    public List<String> getUrls() {
        return urls;
    }
    
    public void setUrls(List<String> urls) {
        this.urls = urls;
    }
    
    public Map<String, String> getCommonHeaders() {
        return commonHeaders;
    }
    
    public void setCommonHeaders(Map<String, String> commonHeaders) {
        this.commonHeaders = commonHeaders;
    }
}