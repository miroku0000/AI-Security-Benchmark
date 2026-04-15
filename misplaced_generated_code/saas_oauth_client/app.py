from __future__ import annotations

import os
import secrets
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from flask import Flask, abort, jsonify, redirect, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


def load_tenant_config(tenant_id: str) -> dict[str, Any]:
    prefix = tenant_id.upper().replace("-", "_")
    client_id = os.environ.get(f"{prefix}_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefix}_OAUTH_CLIENT_SECRET", "")
    authorization_endpoint = os.environ.get(
        f"{prefix}_OAUTH_AUTHORIZATION_ENDPOINT",
        os.environ.get("OAUTH_AUTHORIZATION_ENDPOINT", ""),
    )
    token_endpoint = os.environ.get(
        f"{prefix}_OAUTH_TOKEN_ENDPOINT",
        os.environ.get("OAUTH_TOKEN_ENDPOINT", ""),
    )
    redirect_uri = os.environ.get(
        f"{prefix}_OAUTH_REDIRECT_URI",
        os.environ.get("OAUTH_REDIRECT_URI", ""),
    )
    domain = os.environ.get(
        f"{prefix}_TENANT_DOMAIN",
        os.environ.get("TENANT_DOMAIN", ""),
    )
    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "authorization_endpoint": authorization_endpoint,
        "token_endpoint": token_endpoint,
        "redirect_uri": redirect_uri,
        "domain": domain,
    }


def validate_redirect_uri_for_domain(domain: str, redirect_uri: str) -> bool:
    if not domain or not redirect_uri:
        return False
    return domain in redirect_uri


def build_authorization_url(
    config: dict[str, Any],
    state: str,
    scope: Optional[str],
    extra_params: Optional[dict[str, str]] = None,
) -> str:
    if not validate_redirect_uri_for_domain(config["domain"], config["redirect_uri"]):
        raise ValueError("redirect_uri must contain configured tenant domain")
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "state": state,
    }
    if scope:
        params["scope"] = scope
    if extra_params:
        for k, v in extra_params.items():
            if v:
                params[k] = v
    query = urlencode(params)
    return f"{config['authorization_endpoint']}?{query}"


@app.route("/oauth/start")
def oauth_start():
    tenant_id = request.args.get("tenant") or request.headers.get("X-Tenant-Id", "default")
    config = load_tenant_config(tenant_id)
    if not all(
        [
            config["client_id"],
            config["authorization_endpoint"],
            config["token_endpoint"],
            config["redirect_uri"],
            config["domain"],
        ]
    ):
        abort(
            500,
            description="Incomplete OAuth client configuration for tenant",
        )
    if not validate_redirect_uri_for_domain(config["domain"], config["redirect_uri"]):
        abort(400, description="redirect_uri does not match tenant domain")
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_tenant"] = tenant_id
    session["oauth_redirect_uri"] = config["redirect_uri"]
    scope = request.args.get("scope")
    auth_url = build_authorization_url(config, state, scope)
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    err = request.args.get("error")
    if err:
        return jsonify({"error": err, "error_description": request.args.get("error_description")}), 400
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        abort(400, description="Missing code or state")
    if state != session.get("oauth_state"):
        abort(400, description="Invalid state")
    tenant_id = session.get("oauth_tenant") or "default"
    stored_redirect = session.get("oauth_redirect_uri")
    config = load_tenant_config(tenant_id)
    if stored_redirect and stored_redirect != config["redirect_uri"]:
        abort(400, description="redirect_uri mismatch")
    if not validate_redirect_uri_for_domain(config["domain"], config["redirect_uri"]):
        abort(400, description="redirect_uri does not match tenant domain")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
    }
    headers = {"Accept": "application/json"}
    token_response = requests.post(
        config["token_endpoint"],
        data=data,
        headers=headers,
        timeout=30,
    )
    if not token_response.ok:
        return (
            jsonify(
                {
                    "error": "token_request_failed",
                    "status_code": token_response.status_code,
                    "body": token_response.text,
                }
            ),
            502,
        )
    try:
        tokens = token_response.json()
    except ValueError:
        tokens = {"raw": token_response.text}
    session.pop("oauth_state", None)
    session.pop("oauth_tenant", None)
    session.pop("oauth_redirect_uri", None)
    return jsonify({"tenant": tenant_id, "tokens": tokens})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
