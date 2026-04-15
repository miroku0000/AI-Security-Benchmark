package com.example.samlsp.saml;

import jakarta.annotation.PostConstruct;
import org.opensaml.core.config.InitializationException;
import org.opensaml.core.config.InitializationService;
import org.springframework.stereotype.Component;

@Component
public class OpenSamlBootstrap {
  @PostConstruct
  public void init() throws InitializationException {
    InitializationService.initialize();
  }
}

