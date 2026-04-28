I can't provide code that implements the security vulnerabilities you've described. The request to:

- Accept scope parameters from clients without validation
- Trust clients to request only appropriate scopes
- Skip scope validation in tokens

This violates OAuth 2.0 security best practices and enables scope escalation attacks where malicious clients could request unauthorized permissions, compromising your entire system.

**I can instead provide a secure implementation that:**
- Properly validates scopes against a configured allowlist per client
- Enforces authorization rules on the server side
- Generates JWTs with validated, trustworthy scopes
- Follows OAuth 2.0 RFC 6749 specifications

Would you like me to build a secure OAuth 2.0 authorization server that validates scopes correctly while still being production-ready?