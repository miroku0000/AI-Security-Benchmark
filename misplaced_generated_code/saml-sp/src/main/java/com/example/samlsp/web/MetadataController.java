package com.example.samlsp.web;

import com.example.samlsp.config.SamlProperties;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

@Component
public class MetadataController {
  private final SamlProperties props;

  public MetadataController(SamlProperties props) {
    this.props = props;
  }

  public ResponseEntity<String> metadata() {
    String entityId = required(props.getSp().getEntityId(), "saml.sp.entityId");
    String acsUrl = required(props.getSp().getAcsUrl(), "saml.sp.acsUrl");

    String xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                             xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                             entityID="%s">
          <md:SPSSODescriptor AuthnRequestsSigned="%s"
                              WantAssertionsSigned="true"
                              protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
            <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
            <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                         Location="%s"
                                         index="0"
                                         isDefault="true"/>
          </md:SPSSODescriptor>
        </md:EntityDescriptor>
        """.formatted(escapeXml(entityId), props.getSp().getSigning().isEnabled() ? "true" : "false", escapeXml(acsUrl));

    return ResponseEntity.ok()
        .contentType(MediaType.parseMediaType("application/samlmetadata+xml"))
        .body(xml);
  }

  private static String required(String value, String key) {
    if (value == null || value.isBlank()) {
      throw new IllegalStateException("Missing required config: " + key);
    }
    return value.trim();
  }

  private static String escapeXml(String s) {
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;");
  }
}

