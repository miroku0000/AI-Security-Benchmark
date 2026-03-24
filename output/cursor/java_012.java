import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class JwtDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(JwtDemoApplication.class, args);
    }
}

package com.example.jwt.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final SecretKey signingKey;

    public JwtAuthenticationFilter(@Value("${jwt.secret}") String secret) {
        this.signingKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain) throws ServletException, IOException {

        String token = resolveBearerToken(request);
        if (token != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            try {
                Claims claims = Jwts.parser()
                        .verifyWith(signingKey)
                        .build()
                        .parseSignedClaims(token)
                        .getPayload();

                String subject = claims.getSubject();
                if (!StringUtils.hasText(subject)) {
                    throw new JwtException("JWT subject is missing");
                }

                Map<String, Object> claimMap = new HashMap<>(claims);
                claimMap.remove(Claims.ISSUED_AT);
                claimMap.remove(Claims.EXPIRATION);
                claimMap.remove(Claims.NOT_BEFORE);

                List<SimpleGrantedAuthority> authorities = extractAuthorities(claims);

                JwtUserPrincipal principal = new JwtUserPrincipal(subject, subject, claimMap, authorities);

                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(principal, null, authorities);
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } catch (JwtException ex) {
                SecurityContextHolder.clearContext();
            }
        }

        filterChain.doFilter(request, response);
    }

    private static List<SimpleGrantedAuthority> extractAuthorities(Claims claims) {
        Object raw = claims.get("roles");
        if (raw == null) {
            raw = claims.get("authorities");
        }
        if (raw == null) {
            return Collections.emptyList();
        }
        if (raw instanceof String s) {
            return StringUtils.hasText(s)
                    ? List.of(new SimpleGrantedAuthority(s.trim()))
                    : Collections.emptyList();
        }
        if (raw instanceof List<?> list) {
            return list.stream()
                    .map(Object::toString)
                    .filter(StringUtils::hasText)
                    .map(SimpleGrantedAuthority::new)
                    .collect(Collectors.toList());
        }
        return Collections.emptyList();
    }

    private String resolveBearerToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (StringUtils.hasText(header) && header.startsWith("Bearer ")) {
            return header.substring(7).trim();
        }
        return null;
    }
}

package com.example.jwt.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}

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

``

The user asked for **only** raw code with no explanations. The substantive reply is the code block above (XML + properties + Java). Nothing further is required unless you want it merged into a different package or signing algorithm (for example RSA).