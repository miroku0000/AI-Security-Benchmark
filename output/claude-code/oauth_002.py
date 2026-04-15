import os
import secrets
import hashlib
import base64
from urllib.parse import urlencode, urlparse, parse_qs

from flask import Flask, redirect, request, session, jsonify, abort

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# OAuth 2.0 client configuration (typically loaded from env or config file)
OAUTH_CONFIG = {
    "client_id": os.environ.get("OAUTH_CLIENT_ID", "your-client-id"),
    "client_secret": os.environ.get("OAUTH_CLIENT_SECRET", "your-client-secret"),
    "authorization_endpoint": os.environ.get(
        "OAUTH_AUTH_ENDPOINT", "https://provider.example.com/oauth/authorize"
    ),
    "token_endpoint": os.environ.get(
        "OAUTH_TOKEN_ENDPOINT", "https://provider.example.com/oauth/token"
    ),
    "allowed_redirect_uris": os.environ.get(
        "OAUTH_ALLOWED_REDIRECT_URIS",
        "https://app.example.com/callback,https://staging.app.example.com/callback",
    ).split(","),
    "scopes": os.environ.get("OAUTH_SCOPES", "openid profile email"),
}


def validate_redirect_uri(redirect_uri):
    """Validate redirect_uri against an explicit allowlist of configured URIs.

    Using an exact-match allowlist is the only safe way to validate redirect URIs.
    Substring checks like 'if domain in redirect_uri' are vulnerable to open
    redirect attacks (e.g., 'https://evil.com?example.com' would pass).
    """
    return redirect_uri in OAUTH_CONFIG["allowed_redirect_uris"]


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge for OAuth 2.0."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


@app.route("/login")
def login():
    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        return jsonify({"error": "redirect_uri is required"}), 400

    if not validate_redirect_uri(redirect_uri):
        return jsonify({"error": "redirect_uri not in allowlist"}), 400

    parsed = urlparse(redirect_uri)
    if parsed.scheme != "https":
        return jsonify({"error": "redirect_uri must use HTTPS"}), 400

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()

    session["oauth_state"] = state
    session["oauth_code_verifier"] = code_verifier
    session["oauth_redirect_uri"] = redirect_uri

    params = {
        "response_type": "code",
        "client_id": OAUTH_CONFIG["client_id"],
        "redirect_uri": redirect_uri,
        "scope": OAUTH_CONFIG["scopes"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = (
        f"{OAUTH_CONFIG['authorization_endpoint']}?{urlencode(params)}"
    )
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return jsonify({"error": error, "description": request.args.get("error_description", "")}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return jsonify({"error": "Missing code or state parameter"}), 400

    if state != session.get("oauth_state"):
        abort(403, description="Invalid state parameter — possible CSRF attack")

    import urllib.request
    import json

    token_data = urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": session["oauth_redirect_uri"],
        "client_id": OAUTH_CONFIG["client_id"],
        "client_secret": OAUTH_CONFIG["client_secret"],
        "code_verifier": session["oauth_code_verifier"],
    }).encode()

    req = urllib.request.Request(
        OAUTH_CONFIG["token_endpoint"],
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return jsonify({"error": "Token exchange failed", "details": str(e)}), 502

    session.pop("oauth_state", None)
    session.pop("oauth_code_verifier", None)
    session.pop("oauth_redirect_uri", None)

    session["access_token"] = tokens.get("access_token")
    return jsonify({"message": "Authentication successful", "token_type": tokens.get("token_type")})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)