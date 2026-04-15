package com.example.samlsp.security;

import java.io.Serial;
import java.io.Serializable;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class SamlUserPrincipal implements UserDetails, Serializable {
  @Serial
  private static final long serialVersionUID = 1L;

  private final String nameId;
  private final String assertionId;
  private final String issuer;
  private final Map<String, List<String>> attributes;

  public SamlUserPrincipal(
      String nameId, String assertionId, String issuer, Map<String, List<String>> attributes) {
    this.nameId = nameId;
    this.assertionId = assertionId;
    this.issuer = issuer;
    this.attributes = Map.copyOf(attributes);
  }

  public String getNameId() {
    return nameId;
  }

  public String getAssertionId() {
    return assertionId;
  }

  public String getIssuer() {
    return issuer;
  }

  public Map<String, List<String>> getAttributes() {
    return attributes;
  }

  @Override
  public Collection<? extends GrantedAuthority> getAuthorities() {
    return Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"));
  }

  @Override
  public String getPassword() {
    return null;
  }

  @Override
  public String getUsername() {
    return nameId;
  }

  @Override
  public boolean isAccountNonExpired() {
    return true;
  }

  @Override
  public boolean isAccountNonLocked() {
    return true;
  }

  @Override
  public boolean isCredentialsNonExpired() {
    return true;
  }

  @Override
  public boolean isEnabled() {
    return true;
  }
}
