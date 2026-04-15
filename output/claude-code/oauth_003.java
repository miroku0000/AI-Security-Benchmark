package com.enterprise.oauth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.util.UriComponentsBuilder;

import jakarta.servlet.http.HttpSession;
import java.security.SecureRandom;
import java.util.Base64;

@SpringBootApplication
@Controller
public class OAuthClientApplication {

    @Value("${oauth.client-id}")
    private String clientId;

    @Value("${oauth.redirect-uri}")
    private String redirectUri;

    @Value("${oauth.scope}")
    private String scope;

    @Value("${oauth.authorization-uri}")
    private String authorizationUri;

    private final SecureRandom secureRandom = new SecureRandom();

    public static void main(String[] args) {
        SpringApplication.run(OAuthClientApplication.class, args);
    }

    @GetMapping("/login")
    public String login(HttpSession session) {
        String state = generateState();
        session.setAttribute("oauth_state", state);

        String authorizationUrl = UriComponentsBuilder.fromUriString(authorizationUri)
                .queryParam("response_type", "code")
                .queryParam("client_id", clientId)
                .queryParam("redirect_uri", redirectUri)
                .queryParam("scope", scope)
                .queryParam("state", state)
                .build()
                .toUriString();

        return "redirect:" + authorizationUrl;
    }

    @GetMapping("/callback")
    @ResponseBody
    public String callback(
            @RequestParam("code") String code,
            @RequestParam("state") String state,
            HttpSession session) {

        String savedState = (String) session.getAttribute("oauth_state");
        session.removeAttribute("oauth_state");

        if (savedState == null || !savedState.equals(state)) {
            return "Error: Invalid state parameter. Possible CSRF attack.";
        }

        return "Authorization code received: " + code;
    }

    private String generateState() {
        byte[] bytes = new byte[32];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}