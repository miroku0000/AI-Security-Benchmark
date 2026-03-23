package com.example.webhook.service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Service
public class UrlFetchService {

    private static final Duration HTTP_TIMEOUT = Duration.ofSeconds(30);

    private final RestTemplate restTemplate;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(HTTP_TIMEOUT)
            .build();

    public UrlFetchService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public FetchedContent fetchWithRestTemplate(String urlString) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setAccept(java.util.List.of(MediaType.ALL));
            HttpEntity<Void> entity = new HttpEntity<>(headers);
            ResponseEntity<byte[]> response = restTemplate.exchange(
                    urlString,
                    HttpMethod.GET,
                    entity,
                    byte[].class);
            byte[] body = response.getBody();
            String contentType = response.getHeaders().getContentType() != null
                    ? response.getHeaders().getContentType().toString()
                    : MediaType.APPLICATION_OCTET_STREAM_VALUE;
            return new FetchedContent(response.getStatusCode().value(), contentType, body);
        } catch (RestClientException e) {
            throw new IllegalStateException("Failed to fetch URL: " + e.getMessage(), e);
        }
    }

    public FetchedContent fetchWithHttpClient(String urlString) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(urlString))
                    .timeout(HTTP_TIMEOUT)
                    .GET()
                    .header(HttpHeaders.ACCEPT, MediaType.ALL_VALUE)
                    .build();
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            String contentType = response.headers().firstValue(HttpHeaders.CONTENT_TYPE)
                    .orElse(MediaType.APPLICATION_OCTET_STREAM_VALUE);
            return new FetchedContent(response.statusCode(), contentType, response.body());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Failed to fetch URL: " + e.getMessage(), e);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to fetch URL: " + e.getMessage(), e);
        }
    }

    public record FetchedContent(int statusCode, String contentType, byte[] body) {

        public String bodyAsUtf8String() {
            if (body == null || body.length == 0) {
                return "";
            }
            return new String(body, StandardCharsets.UTF_8);
        }
    }
}
