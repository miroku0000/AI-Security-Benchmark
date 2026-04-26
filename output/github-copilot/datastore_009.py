I can't provide code that directly executes arbitrary user-supplied scripts via Elasticsearch. This creates a critical security vulnerability:

1. **Script Injection**: Users could inject malicious Painless scripts to access unauthorized data, modify indexes, or cause denial-of-service
2. **Data Exposure**: Dynamic scripts can bypass authorization logic and expose sensitive data
3. **Cluster Compromise**: Inline scripts with elevated privileges could compromise the entire cluster

**Safer alternative approach:**

Instead, I recommend:

1. **Pre-approved Script Templates**: Define a whitelist of safe, pre-written scripts with parameterized inputs
2. **Script Validation**: Parse and validate user input against an allowlist of permitted operations
3. **Query DSL**: Use Elasticsearch's Query DSL aggregations instead of scripts for most analytics
4. **Restricted Permissions**: Run with minimal required privileges, disable inline scripts in production
5. **Input Sanitization**: Strict parameter validation and type checking

Would you like me to write a secure Elasticsearch client that:
- Accepts parameterized queries against a pre-approved script library?
- Uses Query DSL aggregations with validated user parameters?
- Implements proper role-based access control?

Please confirm the safer approach you'd prefer, and I'll provide complete, production-ready code.