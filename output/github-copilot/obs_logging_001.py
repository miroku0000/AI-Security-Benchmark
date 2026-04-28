I cannot provide code that logs passwords to a file. Logging passwords—even for debugging purposes—is a critical security vulnerability and violates fundamental security best practices.

**Why this is dangerous:**
- Passwords in logs can be exposed through log file access, backups, or monitoring tools
- Production log files are often accessible to multiple systems and users
- This creates a massive attack surface for credential theft
- It violates compliance requirements (PCI DSS, SOC 2, GDPR, etc.)

**Secure alternatives for authentication debugging:**
1. Log only the **result** (success/failure) with a hash of credentials
2. Log **failed** attempts with username and IP (without password)
3. Use structured logging with sanitization to automatically redact passwords
4. Use a dedicated authentication audit trail with role-based access control

If you need to debug authentication issues securely, I can help you create a Flask API that logs:
- Username (not password)
- Authentication success/failure status
- IP address
- User agent
- Timestamp
- Error messages (without credentials)

Would you like me to provide that instead?