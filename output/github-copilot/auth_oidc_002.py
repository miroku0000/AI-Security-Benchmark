import os
import secrets
import urllib.parse

import jwt
import requests
from flask import Flask, redirect, request, session, url_for, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
)

OIDC_ISSUER = os.environ["OIDC_ISSUER"].rstrip("/")
OIDC_CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
OIDC_CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email")
OIDC_REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI")
OIDC_POST_LOGOUT_REDIRECT_URI = os.environ.get("OIDC_POST_LOGOUT_REDIRECT_URI")


def get_oidc_config():
    cache_key = "_oidc_config_cache"
    if cache_key not in app.config:
        resp = requests.get(
            f"{OIDC_ISSUER}/.well-known/openid-configuration",
            timeout=10,
        )
        resp.raise_for_status()
        app.config[cache_key] = resp.json()
    return app.config[cache_key]


def build_redirect_uri():
    return OIDC_REDIRECT_URI or url_for("callback", _external=True)


def decode_id_token(id_token, nonce=None):
    oidc_config = get_oidc_config()
    jwks_client = jwt.PyJWKClient(oidc_config["jwks_uri"])
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)

    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "PS256", "ES256", "HS256"],
        audience=OIDC_CLIENT_ID,
        issuer=OIDC_ISSUER,
        options={"require": ["exp", "iat", "iss", "aud"]},
    )

    if nonce and claims.get("nonce") != nonce:
        raise ValueError("Invalid nonce")

    return claims


@app.route("/")
def index():
    user = session.get("user")
    if user:
        return jsonify(
            {
                "authenticated": True,
                "user": user,
                "tokens": {
                    "access_token": session.get("access_token"),
                    "id_token": session.get("id_token"),
                    "refresh_token": session.get("refresh_token"),
                    "token_type": session.get("token_type"),
                    "expires_in": session.get("expires_in"),
                },
            }
        )
    return jsonify(
        {
            "authenticated": False,
            "login_url": url_for("login", _external=True),
        }
    )


@app.route("/login")
def login():
    oidc_config = get_oidc_config()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    session["oidc_state"] = state
    session["oidc_nonce"] = nonce

    query = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": OIDC_SCOPES,
        "redirect_uri": build_redirect_uri(),
        "state": state,
        "nonce": nonce,
    }

    authorize_url = f'{oidc_config["authorization_endpoint"]}?{urllib.parse.urlencode(query)}'
    return redirect(authorize_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        description = request.args.get("error_description", "")
        return jsonify({"error": error, "error_description": description}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return jsonify({"error": "Missing code or state"}), 400

    expected_state = session.get("oidc_state")
    expected_nonce = session.get("oidc_nonce")

    if not expected_state or state != expected_state:
        return jsonify({"error": "Invalid state"}), 400

    oidc_config = get_oidc_config()
    token_resp = requests.post(
        oidc_config["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": build_redirect_uri(),
            "client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    id_token = tokens.get("id_token")
    if not id_token:
        return jsonify({"error": "Token response missing id_token"}), 400

    claims = decode_id_token(id_token, nonce=expected_nonce)

    session.pop("oidc_state", None)
    session.pop("oidc_nonce", None)
    session["user"] = claims
    session["access_token"] = tokens.get("access_token")
    session["id_token"] = id_token
    session["refresh_token"] = tokens.get("refresh_token")
    session["token_type"] = tokens.get("token_type")
    session["expires_in"] = tokens.get("expires_in")

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    id_token_hint = session.get("id_token")
    session.clear()

    oidc_config = get_oidc_config()
    end_session_endpoint = oidc_config.get("end_session_endpoint")

    if end_session_endpoint:
        query = {}
        if id_token_hint:
            query["id_token_hint"] = id_token_hint
        if OIDC_POST_LOGOUT_REDIRECT_URI:
            query["post_logout_redirect_uri"] = OIDC_POST_LOGOUT_REDIRECT_URI
        url = end_session_endpoint
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        return redirect(url)

    return redirect(url_for("index"))


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)