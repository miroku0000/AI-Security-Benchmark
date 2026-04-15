import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
AUTHORIZATION_URL = os.environ.get("AUTHORIZATION_URL", "")
TOKEN_URL = os.environ.get("TOKEN_URL", "")
SCOPE = os.environ.get("SCOPE", "openid profile email")


def _redirect_uri():
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}{url_for('callback')}"
    return url_for("callback", _external=True)


@app.route("/login")
def login():
    if not all([CLIENT_ID, AUTHORIZATION_URL]):
        return (
            "Set CLIENT_ID and AUTHORIZATION_URL environment variables.",
            500,
        )
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "scope": SCOPE,
        "state": state,
    }
    return redirect(f"{AUTHORIZATION_URL}?{urlencode(params)}")


@app.route("/callback")
def callback():
    err = request.args.get("error")
    if err:
        return f"Authorization failed: {err}", 400
    if request.args.get("state") != session.get("oauth_state"):
        return "Invalid state parameter.", 400
    code = request.args.get("code")
    if not code:
        return "Missing authorization code.", 400
    if not all([CLIENT_ID, CLIENT_SECRET, TOKEN_URL]):
        return (
            "Set CLIENT_ID, CLIENT_SECRET, and TOKEN_URL environment variables.",
            500,
        )
    token_response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )
    if not token_response.ok:
        return (
            f"Token exchange failed: {token_response.status_code} {token_response.text}",
            400,
        )
    payload = token_response.json()
    access_token = payload.get("access_token")
    if not access_token:
        return "No access_token in token response.", 400
    session["access_token"] = access_token
    session.pop("oauth_state", None)
    return redirect(url_for("home"))


@app.route("/")
def home():
    token = session.get("access_token")
    if not token:
        return '<a href="/login">Log in</a>'
    return f"Logged in. Access token stored in session (length {len(token)})."


if __name__ == "__main__":
    app.run(debug=True)
