"""
OAuth 2.0 Authorization Server with secure redirect URI validation.

Supports multiple registered redirect URIs per client to cover
dev, staging, and prod environments.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler


# --- In-memory stores (use a real database in production) ---

CLIENTS = {
    "demo-client": {
        "client_secret": "demo-secret",
        "redirect_uris": [
            "http://localhost:3000/callback",
            "https://staging.example.com/callback",
            "https://app.example.com/callback",
        ],
        "name": "Demo Application",
    }
}

authorization_codes = {}  # code -> {client_id, redirect_uri, user_id, expires_at, scope}
access_tokens = {}        # token -> {client_id, user_id, expires_at, scope}


def validate_redirect_uri(client_id: str, redirect_uri: str) -> bool:
    """
    Validate redirect URI using exact string matching (RFC 6749 §3.1.2.3).

    Each client registers the full redirect URI for every environment.
    This prevents open-redirect attacks that substring/prefix matching allows.
    """
    client = CLIENTS.get(client_id)
    if not client:
        return False
    return redirect_uri in client["redirect_uris"]


def generate_authorization_code(client_id: str, redirect_uri: str, user_id: str, scope: str) -> str:
    code = secrets.token_urlsafe(32)
    authorization_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "user_id": user_id,
        "scope": scope,
        "expires_at": time.time() + 600,
    }
    return code


def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str):
    code_data = authorization_codes.pop(code, None)
    if not code_data:
        return None, "invalid_grant"
    if code_data["expires_at"] < time.time():
        return None, "invalid_grant"
    if code_data["client_id"] != client_id:
        return None, "invalid_grant"
    # Redirect URI must exactly match the one used in the authorization request
    if code_data["redirect_uri"] != redirect_uri:
        return None, "invalid_grant"
    client = CLIENTS.get(client_id)
    if not client or not hmac.compare_digest(client["client_secret"], client_secret):
        return None, "invalid_client"

    token = secrets.token_urlsafe(32)
    access_tokens[token] = {
        "client_id": client_id,
        "user_id": code_data["user_id"],
        "scope": code_data["scope"],
        "expires_at": time.time() + 3600,
    }
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": code_data["scope"],
    }, None


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/authorize":
            self.handle_authorize(urllib.parse.parse_qs(parsed.query))
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/token":
            length = int(self.headers.get("Content-Length", 0))
            body = urllib.parse.parse_qs(self.rfile.read(length).decode())
            self.handle_token(body)
        else:
            self.send_error(404)

    def handle_authorize(self, params):
        client_id = params.get("client_id", [None])[0]
        redirect_uri = params.get("redirect_uri", [None])[0]
        response_type = params.get("response_type", [None])[0]
        scope = params.get("scope", [""])[0]
        state = params.get("state", [None])[0]

        if response_type != "code":
            self.send_error(400, "unsupported_response_type")
            return

        if not client_id or client_id not in CLIENTS:
            self.send_error(400, "invalid client_id")
            return

        if not redirect_uri or not validate_redirect_uri(client_id, redirect_uri):
            # Do NOT redirect — show error directly to prevent open redirect
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Error: invalid redirect_uri</h1>"
                             b"<p>The redirect URI is not registered for this client.</p>")
            return

        # In production, show a login/consent screen here.
        # For this demo, we auto-approve as user "demo-user".
        code = generate_authorization_code(client_id, redirect_uri, "demo-user", scope)
        redirect_params = {"code": code}
        if state:
            redirect_params["state"] = state
        location = redirect_uri + "?" + urllib.parse.urlencode(redirect_params)

        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def handle_token(self, params):
        grant_type = params.get("grant_type", [None])[0]
        if grant_type != "authorization_code":
            self.send_json(400, {"error": "unsupported_grant_type"})
            return

        code = params.get("code", [None])[0]
        client_id = params.get("client_id", [None])[0]
        client_secret = params.get("client_secret", [None])[0]
        redirect_uri = params.get("redirect_uri", [None])[0]

        if not all([code, client_id, client_secret, redirect_uri]):
            self.send_json(400, {"error": "invalid_request"})
            return

        token_response, error = exchange_code_for_token(code, client_id, client_secret, redirect_uri)
        if error:
            self.send_json(400, {"error": error})
            return

        self.send_json(200, token_response)

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[OAuth] {args[0]}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("127.0.0.1", port), OAuthHandler)
    print(f"OAuth 2.0 Authorization Server running on http://127.0.0.1:{port}")
    print(f"Registered clients: {list(CLIENTS.keys())}")
    server.serve_forever()