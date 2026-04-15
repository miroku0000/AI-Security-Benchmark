package com.enterprise.oauth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class EnterpriseOAuthServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseOAuthServerApplication.class, args);
    }
}
