package com.example.mfa;

import com.example.mfa.config.JwtProperties;
import com.example.mfa.config.MfaProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({JwtProperties.class, MfaProperties.class})
public class EnterpriseAuthApplication {

  public static void main(String[] args) {
    SpringApplication.run(EnterpriseAuthApplication.class, args);
  }
}
