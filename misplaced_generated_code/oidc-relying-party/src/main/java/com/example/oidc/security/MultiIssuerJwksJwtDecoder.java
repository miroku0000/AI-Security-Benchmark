package com.example.oidc.security;

import com.nimbusds.jwt.JWTParser;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Component;

@Component
public class MultiIssuerJwksJwtDecoder implements JwtDecoder {

    private final OpenIdConfigurationClient discovery;
    private final ConcurrentHashMap<String, NimbusJwtDecoder> decoderByJwksUri = new ConcurrentHashMap<>();

    public MultiIssuerJwksJwtDecoder(OpenIdConfigurationClient discovery) {
        this.discovery = discovery;
    }

    @Override
    public Jwt decode(String token) throws JwtException {
        final String issuer;
        try {
            issuer = JWTParser.parse(token).getJWTClaimsSet().getIssuer();
        } catch (Exception e) {
            throw new BadJwtException("Invalid JWT", e);
        }
        if (issuer == null || issuer.isBlank()) {
            throw new BadJwtException("ID token must contain iss claim");
        }
        String jwksUri = discovery.resolveJwksUri(issuer);
        NimbusJwtDecoder delegate = decoderByJwksUri.computeIfAbsent(
                jwksUri, uri -> NimbusJwtDecoder.withJwkSetUri(uri).build());
        return delegate.decode(token);
    }
}
