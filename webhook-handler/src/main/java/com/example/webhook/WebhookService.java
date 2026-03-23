package com.example.webhook;

import com.example.webhook.dto.FetchResponse;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.net.URI;

@Service
public class WebhookService {

    private final RestTemplate restTemplate;

    public WebhookService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public FetchResponse fetchUrl(String urlString) {
        URI uri = URI.create(urlString);
        ResponseEntity<String> response = restTemplate.exchange(
                uri,
                HttpMethod.GET,
                null,
                String.class
        );
        String contentType = response.getHeaders().getContentType() != null
                ? response.getHeaders().getContentType().toString()
                : null;
        return new FetchResponse(response.getStatusCode().value(), contentType, response.getBody());
    }
}
