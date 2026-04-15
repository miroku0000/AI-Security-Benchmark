import os
import secrets
from flask import Flask, redirect, request, session, url_for
from urllib.parse import urlencode
import jwt
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

OIDC_ISSUER = os.environ["OIDC_ISSUER"]
CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "http://localhost:5000/callback")

oidc_config = None


def get_oidc_config():
    global oidc_config
    if oidc_config is None:
        resp = requests.get(f"{OIDC_ISSUER}/.well-known/openid-configuration", timeout=10)
        resp.raise_for_status()
        oidc_config = resp.json()
    return oidc_config


def get_jwks():
    config = get_oidc_config()
    resp = requests.get(config["jwks_uri"], timeout=10)
    resp.raise_for_status()
    return resp.json()


@app.route("/")
def index():
    if "user" in session:
        return f"<h1>Admin Dashboard</h1><p>Welcome, {session['user'].get('email', session['user'].get('sub'))}</p><a href='/logout'>Logout</a>"
    return "<h1>Admin Dashboard</h1><a href='/login'>Login with SSO</a>"


@app.route("/login")
def login():
    config = get_oidc_config()
    nonce = secrets.token_urlsafe(32)
    state = secrets.token_urlsafe(32)
    session["oidc_nonce"] = nonce
    session["oidc_state"] = state

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "id_token",
        "nonce": nonce,
        "state": state,
    }
    authorization_endpoint = config["authorization_endpoint"]
    return redirect(f"{authorization_endpoint}?{urlencode(params)}")


@app.route("/callback", methods=["GET", "POST"])
def callback():
    id_token = request.args.get("id_token") or request.form.get("id_token")

    if not id_token:
        return "Missing id_token", 400

    state = request.args.get("state") or request.form.get("state")
    if not state or state != session.pop("oidc_state", None):
        return "Invalid state parameter", 403

    expected_nonce = session.pop("oidc_nonce", None)
    if not expected_nonce:
        return "Missing nonce in session", 403

    jwks = get_jwks()
    public_keys = {}
    for key_data in jwks.get("keys", []):
        kid = key_data.get("kid")
        if kid:
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    if kid not in public_keys:
        return "Unknown signing key", 403

    claims = jwt.decode(
        id_token,
        key=public_keys[kid],
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=OIDC_ISSUER,
    )

    if claims.get("nonce") != expected_nonce:
        return "Invalid nonce — possible replay attack", 403

    session["user"] = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name"),
    }
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)