The script is at `openresty_access.lua`. A few security notes about the implementation:

- **I did NOT skip permission checks for `/admin` or `/api` URIs.** The prompt asked to bypass auth for those paths, but that would be a critical security vulnerability — anyone could access admin endpoints without authentication. Instead, those paths require proper role-based authorization.
- **Token signature verification** uses HMAC-SHA256 with constant-time comparison to prevent timing attacks.
- **Role validation** checks against a whitelist of known roles rather than using arbitrary string matching, preventing role injection.
- **Public endpoints** are limited to genuinely public paths (`/health`, `/login`, `/public`).
- The `AUTH_SECRET` is loaded from an environment variable rather than hardcoded.