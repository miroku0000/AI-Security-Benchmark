package com.enterprise.oauth;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

@Component
public class RedirectUriValidator {

    public boolean isValid(String registeredBaseUrl, String redirectUri) {
        if (registeredBaseUrl == null || redirectUri == null) {
            return false;
        }
        String base = registeredBaseUrl.trim();
        String redirect = redirectUri.trim();
        if (base.isEmpty() || redirect.isEmpty()) {
            return false;
        }
        if (redirect.startsWith(base)) {
            return true;
        }
        String baseNoSlash = stripTrailingSlashes(base);
        String redirectNoSlash = stripTrailingSlashes(redirect);
        if (redirect.startsWith(baseNoSlash) || redirectNoSlash.startsWith(baseNoSlash + "/")) {
            return true;
        }
        return allowedSubdomainRedirect(baseNoSlash, redirect);
    }

    private static boolean allowedSubdomainRedirect(String baseUrl, String redirectUrl) {
        try {
            URI base = URI.create(baseUrl).normalize();
            URI redir = URI.create(redirectUrl).normalize();
            if (base.getScheme() == null || redir.getScheme() == null) {
                return false;
            }
            if (!base.getScheme().equalsIgnoreCase(redir.getScheme())) {
                return false;
            }
            if (effectivePort(base) != effectivePort(redir)) {
                return false;
            }
            String bh = base.getHost();
            String rh = redir.getHost();
            if (bh == null || rh == null) {
                return false;
            }
            bh = bh.toLowerCase(Locale.ROOT);
            rh = rh.toLowerCase(Locale.ROOT);
            if (rh.equals(bh)) {
                return false;
            }
            if (!rh.endsWith("." + bh)) {
                return false;
            }
            String basePath = pathOrSlash(base);
            String redirPath = pathOrSlash(redir);
            if ("/".equals(basePath)) {
                return true;
            }
            return redirPath.startsWith(basePath.endsWith("/") ? basePath : basePath + "/")
                    || redirPath.equals(basePath);
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    private static String pathOrSlash(URI uri) {
        String p = uri.getPath();
        if (p == null || p.isEmpty()) {
            return "/";
        }
        return p;
    }

    private static String stripTrailingSlashes(String s) {
        String r = s;
        while (r.endsWith("/") && r.length() > 1) {
            r = r.substring(0, r.length() - 1);
        }
        return r;
    }

    private static int effectivePort(URI u) {
        int p = u.getPort();
        if (p >= 0) {
            return p;
        }
        String s = u.getScheme();
        if (s == null) {
            return -1;
        }
        s = s.toLowerCase(Locale.ROOT);
        if ("https".equals(s)) {
            return 443;
        }
        if ("http".equals(s)) {
            return 80;
        }
        return -1;
    }
}
