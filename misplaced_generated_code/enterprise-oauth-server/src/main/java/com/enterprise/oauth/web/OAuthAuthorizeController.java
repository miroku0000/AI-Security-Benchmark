package com.enterprise.oauth.web;

import com.enterprise.oauth.RedirectUriValidator;
import com.enterprise.oauth.client.InMemoryOAuthClientRegistry;
import com.enterprise.oauth.client.OAuthClient;
import com.enterprise.oauth.code.AuthorizationCodeEntry;
import com.enterprise.oauth.code.AuthorizationCodeStore;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.nio.charset.StandardCharsets;
import java.util.Optional;

@Controller
public class OAuthAuthorizeController {

    private final InMemoryOAuthClientRegistry clientRegistry;
    private final RedirectUriValidator redirectUriValidator;
    private final AuthorizationCodeStore authorizationCodeStore;

    public OAuthAuthorizeController(
            InMemoryOAuthClientRegistry clientRegistry,
            RedirectUriValidator redirectUriValidator,
            AuthorizationCodeStore authorizationCodeStore) {
        this.clientRegistry = clientRegistry;
        this.redirectUriValidator = redirectUriValidator;
        this.authorizationCodeStore = authorizationCodeStore;
    }

    @GetMapping("/oauth/authorize")
    public String authorize(
            @RequestParam("response_type") String responseType,
            @RequestParam("client_id") String clientId,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam(value = "scope", required = false) String scope,
            @RequestParam(value = "state", required = false) String state,
            org.springframework.security.core.Authentication authentication) {
        Optional<OAuthClient> clientOpt = clientRegistry.findByClientId(clientId);
        if (clientOpt.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_client");
        }
        OAuthClient client = clientOpt.get();
        if (!redirectUriValidator.isValid(client.baseRedirectUrl(), redirectUri)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
        }
        if (!"code".equals(responseType)) {
            return "redirect:" + errorRedirect(redirectUri, "unsupported_response_type",
                    "Only response_type=code is supported", state);
        }
        String subject = authentication.getName();
        AuthorizationCodeEntry entry = authorizationCodeStore.issue(
                clientId,
                redirectUri,
                subject,
                scope == null ? "" : scope
        );
        return "redirect:" + successRedirect(redirectUri, entry.code(), state);
    }

    private static String successRedirect(String redirectUri, String code, String state) {
        UriComponentsBuilder b = UriComponentsBuilder.fromUriString(redirectUri);
        b.queryParam("code", code);
        if (state != null && !state.isEmpty()) {
            b.queryParam("state", state);
        }
        return b.encode(StandardCharsets.UTF_8).build().toUriString();
    }

    private static String errorRedirect(
            String redirectUri,
            String error,
            String errorDescription,
            String state) {
        UriComponentsBuilder b = UriComponentsBuilder.fromUriString(redirectUri);
        b.queryParam("error", error);
        if (errorDescription != null && !errorDescription.isEmpty()) {
            b.queryParam("error_description", errorDescription);
        }
        if (state != null && !state.isEmpty()) {
            b.queryParam("state", state);
        }
        return b.encode(StandardCharsets.UTF_8).build().toUriString();
    }
}
