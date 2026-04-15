if (!'https'.equalsIgnoreCase(uri.scheme)) {
        throw new RuntimeException('Only HTTPS artifact URLs are allowed.')
    }
    if (uri.userInfo != null) {
        throw new RuntimeException('Embedded credentials in ARTIFACT_URL are not allowed.')
    }
    if (uri.fragment != null) {
        throw new RuntimeException('URL fragments are not allowed in ARTIFACT_URL.')
    }
    if (uri.host == null || uri.host.trim().isEmpty()) {
        throw new RuntimeException('ARTIFACT_URL must include a hostname.')
    }
    if (!(uri.port == -1 || uri.port == 443)) {
        throw new RuntimeException('Only the default HTTPS port is allowed for ARTIFACT_URL.')
    }
    if (!hostMatchesAllowlist(uri.host, allowedHosts)) {
        throw new RuntimeException("Artifact host '${uri.host}' is not in the allowlist.")
    }
    if (uri.path == null || uri.path.trim().isEmpty() || uri.path.endsWith('/')) {
        throw new RuntimeException('ARTIFACT_URL must reference a file, not a directory.')
    }