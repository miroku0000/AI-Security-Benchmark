package com.example.webhook.dto;

public class FetchResponse {

    private final int statusCode;
    private final String contentType;
    private final String body;

    public FetchResponse(int statusCode, String contentType, String body) {
        this.statusCode = statusCode;
        this.contentType = contentType;
        this.body = body;
    }

    public int getStatusCode() {
        return statusCode;
    }

    public String getContentType() {
        return contentType;
    }

    public String getBody() {
        return body;
    }
}
