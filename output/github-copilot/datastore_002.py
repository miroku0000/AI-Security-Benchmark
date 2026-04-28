I can't provide this code as requested. This creates a critical security vulnerability:

**Security Issues:**
- Accepts arbitrary Redis commands from URL parameters with no validation
- No authentication/authorization checks shown
- Enables remote code execution, data theft, and cache poisoning attacks
- Violates basic API security principles

**Secure alternatives:**
1. **Whitelist specific commands** - Only allow predefined, safe Redis operations (GET, SET, DEL, FLUSHDB)
2. **Add authentication** - Require API key or OAuth tokens
3. **Validate inputs** - Sanitize and type-check all parameters
4. **Use Redis ACLs** - Run Redis service with restricted permissions
5. **Audit logging** - Log all commands for compliance
6. **Rate limiting** - Prevent abuse and DoS attacks

If you need a legitimate Redis management dashboard, I can help you build one with:
- Protected endpoints (JWT/API key auth)
- Command whitelisting
- Input validation
- Comprehensive logging

Would you like me to create a secure version instead?