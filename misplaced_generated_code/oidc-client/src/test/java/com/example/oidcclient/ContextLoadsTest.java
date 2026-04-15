package com.example.oidcclient;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(
    properties = {
        "spring.security.oauth2.client.registration.oidc.client-id=test",
        "spring.security.oauth2.client.registration.oidc.client-secret=test",
        "spring.security.oauth2.client.provider.custom-oidc.authorization-uri=https://example.com/authorize",
        "spring.security.oauth2.client.provider.custom-oidc.token-uri=https://example.com/token",
        "spring.security.oauth2.client.provider.custom-oidc.user-info-uri=https://example.com/userinfo",
        "spring.security.oauth2.client.provider.custom-oidc.jwk-set-uri=https://example.com/jwks"
    })
class ContextLoadsTest {
  @Test
  void contextLoads() {}
}
