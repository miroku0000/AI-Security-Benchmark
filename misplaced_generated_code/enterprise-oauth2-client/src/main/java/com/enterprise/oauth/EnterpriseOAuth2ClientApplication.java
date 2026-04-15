package com.enterprise.oauth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

import com.enterprise.oauth.config.OAuthClientProperties;

@SpringBootApplication
@EnableConfigurationProperties(OAuthClientProperties.class)
public class EnterpriseOAuth2ClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseOAuth2ClientApplication.class, args);
    }
}
