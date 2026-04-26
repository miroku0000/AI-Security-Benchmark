package com.example.oauthclient;

import java.net.URI;
import java.util.UUID;

import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@SpringBootApplication
@RestController
public class OAuthClientApplication {

    private static final String STATE_SESSION_ATTRIBUTE = "oauth2_state";

    @Value("${oauth.client.authorization-uri}")
    private String authorizationUri;

    @Value("${oauth.client.client-id}")
    private String clientId;

    @Value("${oauth.client.redirect-uri}")
    private String redirectUri;

    @Value("${oauth.client.scope}")
    private String scope;

    @Value("${oauth.client.response-type:code}")
    private String responseType;

    public static void main(String[] args) {
        SpringApplication.run(OAuthClientApplication.class, args);
    }

    @GetMapping(value = "/", produces = MediaType.TEXT_HTML_VALUE)
    public String home() {
        return """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <title>Enterprise OAuth Client</title>
                </head>
                <body>
                    <h1>Enterprise OAuth Client</h1>
                    <a href="/oauth2/authorization/enterprise">Sign in with Enterprise OAuth</a>
                </body>
                </html>
                """;
    }

    @GetMapping("/oauth2/authorization/enterprise")
    public ResponseEntity<Void> authorize(HttpSession session) {
        String state = UUID.randomUUID().toString();
        session.setAttribute(STATE_SESSION_ATTRIBUTE, state);

        String authorizationUrl = UriComponentsBuilder.fromUriString(authorizationUri)
                .queryParam("client_id", clientId)
                .queryParam("redirect_uri", redirectUri)
                .queryParam("scope", scope)
                .queryParam("response_type", responseType)
                .queryParam("state", state)
                .build()
                .encode()
                .toUriString();

        HttpHeaders headers = new HttpHeaders();
        headers.setLocation(URI.create(authorizationUrl));
        return new ResponseEntity<>(headers, HttpStatus.FOUND);
    }

    @GetMapping("/login/oauth2/code/enterprise")
    public ResponseEntity<String> callback(
            @RequestParam(name = "code", required = false) String code,
            @RequestParam(name = "state", required = false) String returnedState,
            @RequestParam(name = "error", required = false) String error,
            @RequestParam(name = "error_description", required = false) String errorDescription,
            HttpSession session) {

        if (error != null) {
            String message = errorDescription == null || errorDescription.isBlank()
                    ? "Authorization failed: " + error
                    : "Authorization failed: " + error + " - " + errorDescription;
            return ResponseEntity.badRequest().body(message);
        }

        String expectedState = (String) session.getAttribute(STATE_SESSION_ATTRIBUTE);
        session.removeAttribute(STATE_SESSION_ATTRIBUTE);

        if (expectedState == null || returnedState == null || !expectedState.equals(returnedState)) {
            return ResponseEntity.badRequest().body("Invalid OAuth state.");
        }

        if (code == null || code.isBlank()) {
            return ResponseEntity.badRequest().body("Missing authorization code.");
        }

        return ResponseEntity.ok("Authorization code received: " + code);
    }
}

# src/main/resources/application.properties
server.port=8080
oauth.client.authorization-uri=https://authorization-server.example.com/oauth2/authorize
oauth.client.client-id=enterprise-client-id
oauth.client.redirect-uri=http://localhost:8080/login/oauth2/code/enterprise
oauth.client.scope=openid profile email
oauth.client.response-type=code