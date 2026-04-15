import base64
import os
import secrets
from urllib.parse import urlencode

import jwt
import requests
from flask import Flask, redirect, request, session, url_for
from jwt import PyJWKClient

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")


def _discovery():
    issuer = os.environ["OIDC_ISSUER"].rstrip("/")
    url = f"{issuer}/.well-known/openid-configuration"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def _authorize_redirect():
    cfg = _discovery()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    session["oidc_state"] = state
    session["oidc_nonce"] = nonce
    client_id = os.environ["OIDC_CLIENT_ID"]
    redirect_uri = os.environ["OIDC_REDIRECT_URI"]
    scope = os.environ.get("OIDC_SCOPE", "openid profile email")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "nonce": nonce,
    }
    return redirect(f"{cfg['authorization_endpoint']}?{urlencode(params)}")


def _token_request(code: str):
    cfg = _discovery()
    client_id = os.environ["OIDC_CLIENT_ID"]
    client_secret = os.environ.get("OIDC_CLIENT_SECRET", "")
    redirect_uri = os.environ["OIDC_REDIRECT_URI"]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
    }
    headers = {"Accept": "application/json"}
    if client_secret:
        if os.environ.get("OIDC_TOKEN_AUTH") == "basic":
            basic = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {basic}"
        else:
            data["client_secret"] = client_secret
    r = requests.post(cfg["token_endpoint"], data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def _decode_id_token(id_token: str, cfg: dict, nonce: str) -> dict:
    jwks_uri = cfg["jwks_uri"]
    issuer = cfg.get("issuer") or os.environ["OIDC_ISSUER"].rstrip("/")
    client_id = os.environ["OIDC_CLIENT_ID"]
    jwk_client = PyJWKClient(jwks_uri, cache_keys=True)
    signing_key = jwk_client.get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
        audience=client_id,
        issuer=issuer,
    )
    if claims.get("nonce") != nonce:
        raise ValueError("invalid nonce")
    return claims


@app.route("/")
def index():
    if "user" not in session:
        return '<a href="/login">Sign in</a>', 200
    u = session["user"]
    name = u.get("name") or u.get("email") or u.get("sub") or "user"
    return (
        f"<p>Signed in as {name}</p>"
        '<p><a href="/logout">Sign out</a></p>'
    )


@app.route("/login")
def login():
    return _authorize_redirect()


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return (
            f"Error: {request.args.get('error')} "
            f"{request.args.get('error_description', '')}",
            400,
        )
    if request.args.get("state") != session.get("oidc_state"):
        return "Invalid state", 400
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    nonce = session.pop("oidc_nonce", None)
    session.pop("oidc_state", None)
    if not nonce:
        return "Missing nonce", 400
    try:
        tokens = _token_request(code)
    except requests.HTTPError as e:
        return f"Token exchange failed: {e.response.text}", 502
    id_token = tokens.get("id_token")
    if not id_token:
        return "No id_token in token response", 400
    try:
        cfg = _discovery()
        claims = _decode_id_token(id_token, cfg, nonce)
    except Exception:
        return "Invalid id_token", 400
    session["user"] = dict(claims)
    session["access_token"] = tokens.get("access_token")
    session["refresh_token"] = tokens.get("refresh_token")
    session["id_token"] = id_token
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    for name in ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_REDIRECT_URI"):
        if name not in os.environ:
            raise RuntimeError(f"Missing required environment variable: {name}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
