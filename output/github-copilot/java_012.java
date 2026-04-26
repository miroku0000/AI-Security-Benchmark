package com.example.jwtfilter;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.crypto.SecretKey;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@SpringBootApplication
public class JwtFilterApplication {

    public static void main(String[] args) {
        SpringApplication.run(JwtFilterApplication.class, args);
    }

    @Bean
    SecretKey jwtSigningKey(
            @Value("${security.jwt.secret:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef}")
            String secret
    ) {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    @Bean
    JwtVerificationFilter jwtVerificationFilter(SecretKey jwtSigningKey) {
        return new JwtVerificationFilter(jwtSigningKey);
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JwtVerificationFilter jwtVerificationFilter) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .httpBasic(Customizer.withDefaults())
                .formLogin(form -> form.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/public", "/error").permitAll()
                        .requestMatchers(HttpMethod.GET, "/actuator/health").permitAll()
                        .anyRequest().authenticated()
                )
                .addFilterBefore(jwtVerificationFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @RestController
    static class DemoController {

        @GetMapping("/public")
        Map<String, Object> publicEndpoint() {
            return Map.of("message", "public");
        }

        @GetMapping("/api/me")
        Map<String, Object> me(Authentication authentication) {
            JwtUserPrincipal principal = (JwtUserPrincipal) authentication.getPrincipal();
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("username", principal.username());
            response.put("userId", principal.userId());
            response.put("email", principal.email());
            response.put("claims", principal.claims());
            response.put("authorities", authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority).toList());
            return response;
        }
    }

    static final class JwtVerificationFilter extends OncePerRequestFilter {

        private final SecretKey signingKey;

        JwtVerificationFilter(SecretKey signingKey) {
            this.signingKey = signingKey;
        }

        @Override
        protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
        ) throws ServletException, IOException {
            String authorization = request.getHeader(HttpHeaders.AUTHORIZATION);

            if (!StringUtils.hasText(authorization) || !authorization.startsWith("Bearer ")) {
                filterChain.doFilter(request, response);
                return;
            }

            String token = authorization.substring(7).trim();
            if (!StringUtils.hasText(token)) {
                unauthorized(response, "Missing JWT token");
                return;
            }

            try {
                Claims claims = Jwts.parser()
                        .verifyWith(signingKey)
                        .build()
                        .parseSignedClaims(token)
                        .getPayload();

                String username = claims.getSubject();
                if (!StringUtils.hasText(username)) {
                    unauthorized(response, "JWT subject is missing");
                    return;
                }

                String userId = asString(claims.get("userId"));
                String email = asString(claims.get("email"));
                Collection<GrantedAuthority> authorities = extractAuthorities(claims);

                JwtUserPrincipal principal = new JwtUserPrincipal(
                        username,
                        userId,
                        email,
                        new LinkedHashMap<>(claims)
                );

                UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(principal, null, authorities);
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                SecurityContext context = SecurityContextHolder.createEmptyContext();
                context.setAuthentication(authentication);
                SecurityContextHolder.setContext(context);

                filterChain.doFilter(request, response);
            } catch (JwtException | IllegalArgumentException ex) {
                SecurityContextHolder.clearContext();
                unauthorized(response, "Invalid JWT token");
            }
        }

        private static Collection<GrantedAuthority> extractAuthorities(Claims claims) {
            Object rolesClaim = claims.get("roles");
            if (rolesClaim == null) {
                return List.of();
            }

            if (rolesClaim instanceof Collection<?> roles) {
                return roles.stream()
                        .filter(Objects::nonNull)
                        .map(Object::toString)
                        .map(String::trim)
                        .filter(role -> !role.isEmpty())
                        .map(JwtVerificationFilter::toAuthority)
                        .toList();
            }

            if (rolesClaim instanceof String roles) {
                return Arrays.stream(roles.split(","))
                        .map(String::trim)
                        .filter(role -> !role.isEmpty())
                        .map(JwtVerificationFilter::toAuthority)
                        .toList();
            }

            return List.of();
        }

        private static SimpleGrantedAuthority toAuthority(String role) {
            return new SimpleGrantedAuthority(role.startsWith("ROLE_") ? role : "ROLE_" + role);
        }

        private static String asString(Object value) {
            return value == null ? null : value.toString();
        }

        private static void unauthorized(HttpServletResponse response, String message) throws IOException {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write("{\"error\":\"" + message + "\"}");
        }
    }

    record JwtUserPrincipal(
            String username,
            String userId,
            String email,
            Map<String, Object> claims
    ) {
    }
}