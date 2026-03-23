package com.example.webhook.dto;

import jakarta.validation.constraints.NotBlank;

public class WebhookRequest {

    @NotBlank
    private String url;

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }
}
