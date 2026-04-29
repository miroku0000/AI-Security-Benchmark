"""Fake AWS Instance Metadata Service for the SSRF demo.

In production, AWS exposes IMDS at http://169.254.169.254/. We can't
hit that on a laptop, and we don't want the demo to require running
on EC2. This script binds 127.0.0.1:8169 and serves the same response
shape — temporary IAM credentials at /latest/meta-data/iam/security-credentials/<role>.

This stub speaks **IMDSv1** semantics: a plain GET returns credentials
with no token handshake. IMDSv2 (introduced 2019, default for new
instances since 2024) requires a PUT-then-GET dance with a custom
header; the AI's `requests.get(url)` cannot complete that dance, so
an IMDSv2-only instance is not vulnerable to this exact SSRF. Many
AWS accounts still allow IMDSv1 via `HttpTokens: optional` for
backwards compatibility — that's the realistic target. See README
for the full IMDSv1-vs-IMDSv2 discussion.

The slide caveat to read on stage: "in a real environment this URL is
http://169.254.169.254/...; we proxy to localhost for a self-contained
demo. The bug is identical — the AI's fetch_url_content does not
distinguish between an attacker-supplied URL pointing at a partner API
and an attacker-supplied URL pointing at IMDS."
"""

import http.server
import json
import socketserver
import threading

PORT = 8169
ROLE_NAME = "demo-ec2-role"

FAKE_CREDS = {
    "Code": "Success",
    "LastUpdated": "2026-04-27T22:00:00Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": "ASIAFAKEDEMO00000000",
    "SecretAccessKey": "ZmFrZURlbW9TZWNyZXRGb3JEZWZjb25TbGlkZQ==",
    "Token": "FwoFAKE/SSRF/demo/token//PROD/would/be/much/longer//==",
    "Expiration": "2026-04-27T28:00:00Z",
}


class IMDSHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/latest/meta-data/iam/security-credentials/":
            body = ROLE_NAME.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == f"/latest/meta-data/iam/security-credentials/{ROLE_NAME}":
            body = json.dumps(FAKE_CREDS, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, fmt, *args):
        # Quiet by default; print to stderr only on errors
        pass


def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), IMDSHandler) as httpd:
        print(f"Fake IMDS listening on http://127.0.0.1:{PORT}/")
        print(f"  /latest/meta-data/iam/security-credentials/")
        print(f"  /latest/meta-data/iam/security-credentials/{ROLE_NAME}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down")


if __name__ == "__main__":
    main()
