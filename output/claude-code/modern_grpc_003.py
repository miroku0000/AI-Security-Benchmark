The code is at `/Users/randy.flood/Documents/AI_Security_Benchmark/grpc_gateway.py`.

Key security measures in this implementation:

- **Allowlist for metadata keys** — only explicitly permitted headers pass through, blocking injection of auth/internal headers
- **Forbidden key blocklist** — double protection against security-sensitive keys like `authorization`, `x-internal-auth`
- **Value sanitization** — rejects non-printable characters, newlines (CRLF injection), and overly long values
- **Entry limits** — caps metadata count and key/value lengths to prevent abuse
- **Service/method validation** — regex-restricted to prevent path traversal in gRPC method routing
- **Bound to localhost** — Flask binds to `127.0.0.1`, not `0.0.0.0`