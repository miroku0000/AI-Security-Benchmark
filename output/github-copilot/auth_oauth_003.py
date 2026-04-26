import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, request, session, url_for


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


app = Flask(__name__)
app.config["SECRET_KEY"] = _required_env("FLASK_SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"

CLIENT_ID = _required_env("OAUTH_CLIENT_ID")
CLIENT_SECRET = _required_env("OAUTH_CLIENT_SECRET")
AUTHORIZATION_URL = _required_env("OAUTH_AUTHORIZATION_URL")
TOKEN_URL = _required_env("OAUTH_TOKEN_URL")
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://127.0.0.1:5000/callback")
SCOPE = os.environ.get("OAUTH_SCOPE", "openid profile email")


@app.route("/login")
def login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
    }

    return redirect(f"{AUTHORIZATION_URL}?{urlencode(params)}")


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        description = request.args.get("error_description", "Authorization failed")
        return f"{error}: {description}", 400

    state = request.args.get("state")
    expected_state = session.get("oauth_state")
    if not state or not expected_state or state != expected_state:
        return "Invalid OAuth state", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    token_response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )

    if not token_response.ok:
        return f"Token exchange failed: {token_response.text}", 400

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return "Token response did not include an access_token", 400

    session.pop("oauth_state", None)
    session["access_token"] = access_token

    return "Login successful"


@app.route("/")
def index():
    if "access_token" in session:
        return "Authenticated"
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_ENV") == "development")