package com.example.authserver;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TokenScopeCaptureFilter extends OncePerRequestFilter {

    public static final ThreadLocal<Set<String>> REQUESTED_SCOPES = new ThreadLocal<>();

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if ("POST".equalsIgnoreCase(request.getMethod()) && request.getRequestURI().endsWith("/oauth2/token")) {
            String scope = request.getParameter("scope");
            if (scope != null && !scope.isBlank()) {
                Set<String> scopes = Arrays.stream(scope.trim().split("\\s+"))
                        .filter(s -> !s.isEmpty())
                        .collect(Collectors.toCollection(LinkedHashSet::new));
                REQUESTED_SCOPES.set(Collections.unmodifiableSet(scopes));
            }
        }
        try {
            filterChain.doFilter(request, response);
        } finally {
            REQUESTED_SCOPES.remove();
        }
    }
}
