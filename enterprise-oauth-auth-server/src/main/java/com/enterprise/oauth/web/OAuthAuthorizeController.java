package com.enterprise.oauth.web;

import com.enterprise.oauth.model.RegisteredClient;
import com.enterprise.oauth.registry.ClientRegistry;
import com.enterprise.oauth.security.RedirectUriValidator;
import com.enterprise.oauth.service.AuthorizationCodeService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
public class OAuthAuthorizeController {

    private final ClientRegistry clientRegistry;
    private final RedirectUriValidator redirectUriValidator;
    private final AuthorizationCodeService authorizationCodeService;

    public OAuthAuthorizeController(
            ClientRegistry clientRegistry,
            RedirectUriValidator redirectUriValidator,
            AuthorizationCodeService authorizationCodeService
    ) {
        this.clientRegistry = clientRegistry;
        this.redirectUriValidator = redirectUriValidator;
        this.authorizationCodeService = authorizationCodeService;
    }

    @GetMapping("/oauth/authorize")
    public void authorize(
            @RequestParam("response_type") String responseType,
            @RequestParam("client_id") String clientId,
            @RequestParam("redirect_uri") String redirectUri,
            @RequestParam(value = "scope", required = false) String scope,
            @RequestParam(value = "state", required = false) String state,
            @RequestHeader(value = "X-Resource-Owner", defaultValue = "enterprise-user") String resourceOwner,
            HttpServletResponse response
    ) {
        if (!"code".equals(responseType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_response_type");
        }

        RegisteredClient client = clientRegistry.findByClientId(clientId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_client"));

        if (!redirectUriValidator.isAllowed(redirectUri, client.baseUrl())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_redirect_uri");
        }

        Set<String> scopes = parseScopes(scope);
        String code = authorizationCodeService.issue(clientId, redirectUri, resourceOwner, scopes);

        URI location = buildRedirectLocation(redirectUri, code, state);
        response.setStatus(HttpServletResponse.SC_FOUND);
        response.setHeader("Location", location.toString());
    }

    private static Set<String> parseScopes(String scope) {
        if (!StringUtils.hasText(scope)) {
            return Set.of();
        }
        return Arrays.stream(scope.split("\\s+"))
                .map(String::trim)
                .filter(StringUtils::hasText)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private static URI buildRedirectLocation(String redirectUri, String code, String state) {
        UriComponentsBuilder b = UriComponentsBuilder.fromUriString(redirectUri)
                .replaceQueryParam("code", code);
        if (StringUtils.hasText(state)) {
            b.replaceQueryParam("state", state);
        }
        String built = b.encode(StandardCharsets.UTF_8).toUriString();
        return URI.create(built);
    }
}
