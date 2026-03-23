package com.example.jwt.security;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.Collections;
import java.util.Map;

public class JwtUserPrincipal implements UserDetails {

    private final String username;
    private final String subject;
    private final Map<String, Object> claims;
    private final Collection<? extends GrantedAuthority> authorities;

    public JwtUserPrincipal(
            String username,
            String subject,
            Map<String, Object> claims,
            Collection<? extends GrantedAuthority> authorities) {
        this.username = username;
        this.subject = subject;
        this.claims = claims != null ? Map.copyOf(claims) : Collections.emptyMap();
        this.authorities = authorities;
    }

    public String getSubject() {
        return subject;
    }

    public Map<String, Object> getClaims() {
        return claims;
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public String getPassword() {
        return null;
    }

    @Override
    public String getUsername() {
        return username;
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
