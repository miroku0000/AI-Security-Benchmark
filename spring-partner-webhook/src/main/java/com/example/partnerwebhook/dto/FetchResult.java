package com.example.partnerwebhook.dto;

import org.springframework.http.HttpStatusCode;

import java.util.Map;

public class FetchResult {

    private final int statusCode;
    private final String body;
    private final Map<String, String> responseHeaders;

    public FetchResult(HttpStatusCode status, String body, Map<String, String> responseHeaders) {
        this.statusCode = status.value();
        this.body = body;
        this.responseHeaders = responseHeaders;
    }

    public int getStatusCode() {
        return statusCode;
    }

    public String getBody() {
        return body;
    }

    public Map<String, String> getResponseHeaders() {
        return responseHeaders;
    }
}
