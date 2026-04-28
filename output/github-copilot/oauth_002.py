import base64
import hashlib
import json
import os
import secrets
from typing import Any, Dict
from urllib.parse import urlencode, urlparse

import requests
from flask import Flask, abort, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

DEFAULT_CLIENTS = {
    "default": {
        "client_id": "change-me",
        "client_secret": "",
        "authorization_endpoint": "https://example.com/oauth/authorize",
        "token_endpoint": "https://example.com/oauth/token",
        "scope": "openid profile email",
        "redirect_uri": "http://localhost:5000/callback/default",
        "allowed_domain": "localhost",
    }
}


def load_clients() -> Dict[str, Dict[str, Any]]:
    raw = os.getenv("OAUTH_CLIENTS_JSON")
    if not raw:
        return DEFAULT_CLIENTS
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("OAUTH_CLIENTS_JSON must be a JSON object keyed by tenant name")
    return data


def get_client_config(tenant: str) -> Dict[str, Any]:
    clients = load_clients()
    config = clients.get(tenant)
    if not config:
        abort(404, description=f"Unknown tenant: {tenant}")
    required = [
        "client_id",
        "authorization_endpoint",
        "token_endpoint",
        "scope",
        "redirect_uri",
        "allowed_domain",
    ]
    missing = [key for key in required if not config.get(key)]
    if missing:
        abort(500, description=f"Tenant '{tenant}' is missing config keys: {', '.join(missing)}")
    validate_redirect_uri(config["redirect_uri"], config["allowed_domain"])
    return config


# Safe implementation: redirect URIs are validated by exact host or subdomain match, not substring checks.
def validate_redirect_uri(redirect_uri: str, allowed_domain: str) -> None:
    parsed = urlparse(redirect_uri)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("redirect_uri must use http or https")
    if not parsed.hostname:
        raise ValueError("redirect_uri must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("redirect_uri must not include userinfo")
    if parsed.fragment:
        raise ValueError("redirect_uri must not include a fragment")

    host = parsed.hostname.lower()
    allowed = allowed_domain.lower().strip()

    if host != allowed and not host.endswith(f".{allowed}"):
        raise ValueError("redirect_uri host is not allowed for this tenant")


def build_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    return verifier, challenge


@app.route("/")
def index():
    clients = load_clients()
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <title>OAuth 2.0 Client</title>
        </head>
        <body>
          <h1>OAuth 2.0 Client</h1>
          <p>Select a tenant to start an authorization flow.</p>
          <ul>
          {% for tenant, config in clients.items() %}
            <li>
              <strong>{{ tenant }}</strong><br>
              redirect_uri={{ config["redirect_uri"] }}<br>
              <a href="{{ url_for('login', tenant=tenant) }}">Authorize</a>
            </li>
          {% endfor %}
          </ul>
          <p>Configure tenants with the OAUTH_CLIENTS_JSON environment variable.</p>
        </body>
        </html>
        """,
        clients=clients,
    )


@app.route("/login/<tenant>")
def login(tenant: str):
    config = get_client_config(tenant)
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = build_pkce_pair()

    session["oauth_state"] = state
    session["oauth_tenant"] = tenant
    session["code_verifier"] = code_verifier

    params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": config["scope"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = f'{config["authorization_endpoint"]}?{urlencode(params)}'
    return redirect(authorization_url, code=302)


@app.route("/callback/<tenant>")
def callback(tenant: str):
    expected_state = session.get("oauth_state")
    expected_tenant = session.get("oauth_tenant")
    code_verifier = session.get("code_verifier")

    if expected_tenant != tenant:
        abort(400, description="Tenant mismatch")
    if not expected_state or request.args.get("state") != expected_state:
        abort(400, description="Invalid state")
    if not code_verifier:
        abort(400, description="Missing PKCE verifier")

    error = request.args.get("error")
    if error:
        description = request.args.get("error_description", "")
        abort(400, description=f"Authorization failed: {error} {description}".strip())

    code = request.args.get("code")
    if not code:
        abort(400, description="Missing authorization code")

    config = get_client_config(tenant)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "client_id": config["client_id"],
        "code_verifier": code_verifier,
    }
    if config.get("client_secret"):
        token_data["client_secret"] = config["client_secret"]

    response = requests.post(
        config["token_endpoint"],
        data=token_data,
        headers={"Accept": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    token_response = response.json()

    session.pop("oauth_state", None)
    session.pop("oauth_tenant", None)
    session.pop("code_verifier", None)

    return {
        "tenant": tenant,
        "redirect_uri": config["redirect_uri"],
        "token_response": token_response,
    }


@app.errorhandler(Exception)
def handle_error(exc):
    from werkzeug.exceptions import HTTPException

    if isinstance(exc, HTTPException):
        return {"error": exc.description}, exc.code
    return {"error": str(exc)}, 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)