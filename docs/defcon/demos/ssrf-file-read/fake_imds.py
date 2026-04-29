"""Fake AWS Instance Metadata Service for the ssrf-file-read demo.

Same shape as demos/ssrf/fake_imds.py — IMDSv1 semantics — bound on
a different port (8170 vs 8169) so both demos can run side by side.
See the sibling ssrf demo's README for the full IMDSv1 vs IMDSv2
discussion. The fake_imds for THIS demo is identical in behavior;
the difference between the two demos is in the AI's URL fetcher,
not the metadata stub.

This stub speaks IMDSv1 semantics: a plain GET returns credentials
with no token handshake. The AI's `urllib.request.urlopen` here is
configurable enough to issue PUTs and add custom headers, so unlike
the gpt-4 ssrf demo, this AI output COULD theoretically defeat
IMDSv2 — though the demo only walks through the IMDSv1 path because
the harness IMDS only speaks v1.
"""

import http.server
import json
import socketserver

PORT = 8170
ROLE_NAME = "demo-ec2-role"

FAKE_CREDS = {
    "Code": "Success",
    "LastUpdated": "2026-04-28T22:00:00Z",
    "Type": "AWS-HMAC",
    "AccessKeyId": "ASIAFAKEDEMO00000000",
    "SecretAccessKey": "ZmFrZURlbW9TZWNyZXRGb3JEZWZjb25TbGlkZQ==",
    "Token": "FwoFAKE/SSRF/demo/token//PROD/would/be/much/longer//==",
    "Expiration": "2026-04-28T28:00:00Z",
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
        pass


def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), IMDSHandler) as httpd:
        print(f"Fake IMDS listening on http://127.0.0.1:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down")


if __name__ == "__main__":
    main()
