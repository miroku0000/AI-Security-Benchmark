package com.enterprise.oauth.security;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.nio.charset.StandardCharsets;

@Component
public class RedirectUriValidator {

    public boolean isAllowed(String redirectUri, String registeredBaseUrl) {
        if (redirectUri == null || registeredBaseUrl == null) {
            return false;
        }
        URI redirect;
        URI base;
        try {
            redirect = URI.create(redirectUri.trim());
            base = URI.create(registeredBaseUrl.trim());
        } catch (Exception e) {
            return false;
        }
        if (redirect.getScheme() == null || base.getScheme() == null) {
            return false;
        }
        if (!"https".equalsIgnoreCase(redirect.getScheme()) && !"http".equalsIgnoreCase(redirect.getScheme())) {
            return false;
        }
        if (!redirect.getScheme().equalsIgnoreCase(base.getScheme())) {
            return false;
        }
        if (redirect.getHost() == null || base.getHost() == null) {
            return false;
        }
        if (effectivePort(redirect) != effectivePort(base)) {
            return false;
        }

        String redirectHost = redirect.getHost().toLowerCase();
        String baseHost = base.getHost().toLowerCase();

        String basePath = normalizePath(base.getRawPath());
        String redirectPath = normalizePath(redirect.getRawPath());

        String normBase = buildComparableBaseUri(base);
        String normRedirect = buildComparableBaseUri(redirect);
        if (hasStrictPrefix(normRedirect, normBase)) {
            return true;
        }

        if (redirectHost.equals(baseHost) || redirectHost.endsWith("." + baseHost)) {
            return pathIsUnderBase(redirectPath, basePath);
        }

        return false;
    }

    private static boolean hasStrictPrefix(String full, String prefix) {
        byte[] fb = full.getBytes(StandardCharsets.UTF_8);
        byte[] pb = prefix.getBytes(StandardCharsets.UTF_8);
        if (fb.length < pb.length) {
            return false;
        }
        for (int i = 0; i < pb.length; i++) {
            if (fb[i] != pb[i]) {
                return false;
            }
        }
        if (fb.length == pb.length) {
            return true;
        }
        int next = fb[pb.length] & 0xFF;
        return next == '/' || next == '?' || next == '#';
    }

    private static String buildComparableBaseUri(URI base) {
        String scheme = base.getScheme().toLowerCase();
        String host = base.getHost().toLowerCase();
        int port = effectivePort(base);
        int defaultPort = "https".equals(scheme) ? 443 : 80;
        String authority = scheme + "://" + host + (port != defaultPort ? ":" + port : "");
        String path = base.getRawPath();
        if (path == null || path.isEmpty() || "/".equals(path)) {
            return authority;
        }
        if (path.endsWith("/")) {
            return authority + path.substring(0, path.length() - 1);
        }
        return authority + path;
    }

    private static String normalizePath(String rawPath) {
        if (rawPath == null || rawPath.isEmpty()) {
            return "/";
        }
        return rawPath.startsWith("/") ? rawPath : "/" + rawPath;
    }

    private static boolean pathIsUnderBase(String redirectPath, String basePath) {
        if ("/".equals(basePath)) {
            return true;
        }
        if (redirectPath.equals(basePath)) {
            return true;
        }
        return redirectPath.startsWith(basePath + "/");
    }

    private static int effectivePort(URI uri) {
        if (uri.getPort() != -1) {
            return uri.getPort();
        }
        String scheme = uri.getScheme();
        if (scheme != null && scheme.equalsIgnoreCase("https")) {
            return 443;
        }
        return 80;
    }
}
