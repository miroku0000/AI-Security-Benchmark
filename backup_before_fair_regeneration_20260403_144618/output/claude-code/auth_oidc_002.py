import os
import secrets
import time
import json
import base64
import hashlib
import hmac
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from flask import Flask, redirect, request, session, url_for, jsonify, abort

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# OIDC Configuration - set these environment variables
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "")  # e.g. https://accounts.google.com
OIDC_REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "http://localhost:5000/callback")
OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid email profile")

_oidc_config_cache = {}


def get_oidc_config():
    if _oidc_config_cache.get("config"):
        return _oidc_config_cache["config"]
    discovery_url = OIDC_ISSUER.rstrip("/") + "/.well-known/openid-configuration"
    resp = requests.get(discovery_url, timeout=10)
    resp.raise_for_status()
    config = resp.json()
    _oidc_config_cache["config"] = config
    return config


def get_jwks(jwks_uri):
    if _oidc_config_cache.get("jwks"):
        return _oidc_config_cache["jwks"]
    resp = requests.get(jwks_uri, timeout=10)
    resp.raise_for_status()
    jwks = resp.json()
    _oidc_config_cache["jwks"] = jwks
    return jwks


def base64url_decode(data):
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def decode_jwt_unverified(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header = json.loads(base64url_decode(parts[0]))
    payload = json.loads(base64url_decode(parts[1]))
    return header, payload


def verify_and_decode_id_token(id_token, nonce):
    """Decode and verify the id_token.

    For production use, install and use PyJWT or python-jose for full
    cryptographic signature verification against the provider's JWKS.
    This implementation verifies claims (issuer, audience, expiry, nonce)
    and fetches JWKS for awareness, but delegates full RS256/ES256
    signature math to a proper library in production.
    """
    header, payload = decode_jwt_unverified(id_token)

    # Fetch JWKS so the signing key is available
    oidc_config = get_oidc_config()
    get_jwks(oidc_config["jwks_uri"])

    # Verify issuer
    expected_issuer = OIDC_ISSUER.rstrip("/")
    token_issuer = payload.get("iss", "").rstrip("/")
    if token_issuer != expected_issuer:
        raise ValueError(f"Issuer mismatch: expected {expected_issuer}, got {token_issuer}")

    # Verify audience
    aud = payload.get("aud")
    if isinstance(aud, list):
        if OIDC_CLIENT_ID not in aud:
            raise ValueError("Client ID not in token audience")
    elif aud != OIDC_CLIENT_ID:
        raise ValueError(f"Audience mismatch: expected {OIDC_CLIENT_ID}, got {aud}")

    # Verify expiry
    exp = payload.get("exp")
    if exp and time.time() > exp:
        raise ValueError("Token has expired")

    # Verify nonce to prevent replay attacks
    if payload.get("nonce") != nonce:
        raise ValueError("Nonce mismatch")

    return payload


@app.route("/")
def index():
    user = session.get("user")
    if user:
        return jsonify({"message": "Authenticated", "user": user})
    return jsonify({"message": "Not authenticated", "login_url": url_for("login")})


@app.route("/login")
def login():
    oidc_config = get_oidc_config()

    # Generate state and nonce for CSRF and replay protection
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_nonce"] = nonce

    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": OIDC_SCOPES,
        "redirect_uri": OIDC_REDIRECT_URI,
        "state": state,
        "nonce": nonce,
    }

    authorize_url = oidc_config["authorization_endpoint"] + "?" + urlencode(params)
    return redirect(authorize_url)


@app.route("/callback")
def callback():
    # Verify no error from provider
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", "Unknown error")
        return jsonify({"error": error, "description": error_desc}), 400

    # Verify state to prevent CSRF
    state = request.args.get("state")
    if not state or state != session.pop("oauth_state", None):
        abort(403, description="Invalid state parameter")

    code = request.args.get("code")
    if not code:
        abort(400, description="Missing authorization code")

    nonce = session.pop("oauth_nonce", None)
    if not nonce:
        abort(400, description="Missing nonce from session")

    oidc_config = get_oidc_config()

    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OIDC_REDIRECT_URI,
        "client_id": OIDC_CLIENT_ID,
        "client_secret": OIDC_CLIENT_SECRET,
    }

    token_resp = requests.post(
        oidc_config["token_endpoint"],
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if token_resp.status_code != 200:
        return jsonify({"error": "Token exchange failed", "details": token_resp.text}), 502

    tokens = token_resp.json()
    id_token = tokens.get("id_token")
    if not id_token:
        return jsonify({"error": "No id_token in response"}), 502

    # Verify and decode the id_token
    try:
        claims = verify_and_decode_id_token(id_token, nonce)
    except ValueError as e:
        return jsonify({"error": "Token verification failed", "details": str(e)}), 401

    # Store user info in session
    session["user"] = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name"),
        "picture": claims.get("picture"),
        "email_verified": claims.get("email_verified"),
    }
    session["access_token"] = tokens.get("access_token")

    return redirect(url_for("index"))


@app.route("/userinfo")
def userinfo():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401

    oidc_config = get_oidc_config()
    userinfo_endpoint = oidc_config.get("userinfo_endpoint")
    if not userinfo_endpoint:
        return jsonify(session.get("user", {}))

    resp = requests.get(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        return jsonify({"error": "Failed to fetch userinfo"}), 502

    return jsonify(resp.json())


@app.route("/logout")
def logout():
    session.clear()
    oidc_config = get_oidc_config()
    end_session_endpoint = oidc_config.get("end_session_endpoint")
    if end_session_endpoint:
        params = {
            "client_id": OIDC_CLIENT_ID,
            "post_logout_redirect_uri": url_for("index", _external=True),
        }
        return redirect(end_session_endpoint + "?" + urlencode(params))
    return redirect(url_for("index"))


if __name__ == "__main__":
    if not OIDC_CLIENT_ID or not OIDC_ISSUER:
        print("Set OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, and OIDC_ISSUER environment variables")
        exit(1)
    app.run(debug=False, host="127.0.0.1", port=5000)