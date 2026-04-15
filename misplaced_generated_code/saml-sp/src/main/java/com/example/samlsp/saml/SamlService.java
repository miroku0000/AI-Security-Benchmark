package com.example.samlsp.saml;

import com.example.samlsp.config.SamlProperties;
import org.springframework.stereotype.Service;

@Service
public class SamlService {
  private final SamlAssertionValidator validator;

  public SamlService(SamlProperties props) {
    this.validator = new SamlAssertionValidator(props);
  }

  public SamlAssertionValidator.ValidatedSaml validate(String samlResponseBase64) {
    return validator.validateHttpPostSamlResponse(samlResponseBase64);
  }
}

