package com.example.sso;

import java.io.IOException;
import java.net.URI;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.stereotype.Controller;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;

@SpringBootApplication
public class SsoLogoutApplication {

    public static void main(String[] args) {
        SpringApplication.run(SsoLogoutApplication.class, args);
    }

    @Controller
    static class LogoutController {

        private final Set<String> allowedRedirectHosts;

        LogoutController(@Value("${sso.allowed-redirect-hosts:}") String allowedRedirectHosts) {
            this.allowedRedirectHosts = Arrays.stream(allowedRedirectHosts.split(","))
                    .map(String::trim)
                    .filter(StringUtils::hasText)
                    .map(host -> host.toLowerCase(Locale.ROOT))
                    .collect(Collectors.toUnmodifiableSet());
        }

        @GetMapping("/logout")
        public void logout(HttpServletRequest request, HttpServletResponse response) throws IOException, ServletException {
            HttpSession session = request.getSession(false);
            if (session != null) {
                session.invalidate();
            }

            request.logout();
            response.sendRedirect(resolveRedirectTarget(request.getParameter("next")));
        }

        private String resolveRedirectTarget(String next) {
            if (!StringUtils.hasText(next)) {
                return "/";
            }

            URI uri;
            try {
                uri = URI.create(next);
            } catch (IllegalArgumentException ex) {
                return "/";
            }

            if (!uri.isAbsolute()) {
                return next.startsWith("/") && !next.startsWith("//") ? next : "/";
            }

            String scheme = uri.getScheme();
            String host = uri.getHost();

            if ((scheme == null || (!scheme.equalsIgnoreCase("http") && !scheme.equalsIgnoreCase("https")))
                    || !StringUtils.hasText(host)) {
                return "/";
            }

            return allowedRedirectHosts.contains(host.toLowerCase(Locale.ROOT)) ? uri.toString() : "/";
        }
    }
}