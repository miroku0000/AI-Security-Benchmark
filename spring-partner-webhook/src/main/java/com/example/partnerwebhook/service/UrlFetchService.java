package com.example.partnerwebhook.service;

import com.example.partnerwebhook.dto.FetchResult;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class UrlFetchService {

    private final HttpClient httpClient;

    public UrlFetchService(HttpClient httpClient) {
        this.httpClient = httpClient;
    }

    public FetchResult fetch(String urlString, Map<String, String> optionalHeaders) {
        URI uri = URI.create(urlString);
        HttpRequest.Builder builder = HttpRequest.newBuilder(uri)
                .timeout(Duration.ofSeconds(30))
                .GET();
        if (optionalHeaders != null) {
            optionalHeaders.forEach(builder::header);
        }
        HttpRequest request = builder.build();
        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            Map<String, String> out = new LinkedHashMap<>();
            response.headers().map().forEach((name, values) -> {
                if (!values.isEmpty()) {
                    out.put(name, String.join(", ", values));
                }
            });
            HttpStatusCode status = HttpStatusCode.valueOf(response.statusCode());
            return new FetchResult(status, response.body() != null ? response.body() : "", Map.copyOf(out));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Failed to fetch URL: " + e.getMessage(), e);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to fetch URL: " + e.getMessage(), e);
        }
    }
}
