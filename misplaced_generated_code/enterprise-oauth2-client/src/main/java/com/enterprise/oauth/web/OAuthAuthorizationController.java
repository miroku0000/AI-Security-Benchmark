package com.enterprise.oauth.web;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

import com.enterprise.oauth.config.OAuthClientProperties;

@RestController
public class OAuthAuthorizationController {

    private final OAuthClientProperties properties;

    public OAuthAuthorizationController(OAuthClientProperties properties) {
        this.properties = properties;
    }

    @GetMapping("/oauth2/authorize")
    public ResponseEntity<Void> redirectToAuthorizationServer() {
        String location = UriComponentsBuilder
                .fromUriString(properties.getAuthorizationEndpoint())
                .queryParam("client_id", properties.getClientId())
                .queryParam("redirect_uri", properties.getRedirectUri())
                .queryParam("scope", properties.getScope())
                .queryParam("response_type", properties.getResponseType())
                .encode()
                .build()
                .toUriString();
        return ResponseEntity
                .status(HttpStatus.FOUND)
                .header(HttpHeaders.LOCATION, location)
                .build();
    }

    @GetMapping("/oauth2/callback")
    public String authorizationCallback(
            @RequestParam(value = "code", required = false) String code,
            @RequestParam(value = "error", required = false) String error,
            @RequestParam(value = "error_description", required = false) String errorDescription) {
        if (error != null) {
            return "error=" + error + (errorDescription != null ? ("&error_description=" + errorDescription) : "");
        }
        return "code=" + (code != null ? code : "");
    }
}
