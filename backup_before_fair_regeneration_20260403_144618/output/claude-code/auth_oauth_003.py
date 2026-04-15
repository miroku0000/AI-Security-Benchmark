import os
import secrets
from flask import Flask, redirect, request, session, url_for, jsonify
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "your-client-id")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "your-client-secret")
OAUTH_AUTHORIZE_URL = os.environ.get("OAUTH_AUTHORIZE_URL", "https://authorization-server.example.com/authorize")
OAUTH_TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL", "https://authorization-server.example.com/token")
OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:5000/callback")
OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE", "openid profile email")


@app.route("/")
def index():
    if "access_token" in session:
        return jsonify({"status": "authenticated", "message": "You are logged in."})
    return jsonify({"status": "unauthenticated", "login_url": url_for("login")})


@app.route("/login")
def login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": OAUTH_SCOPE,
        "state": state,
    }
    authorize_url = requests.Request("GET", OAUTH_AUTHORIZE_URL, params=params).prepare().url
    return redirect(authorize_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return jsonify({"error": error, "description": request.args.get("error_description", "")}), 400

    state = request.args.get("state")
    if not state or state != session.pop("oauth_state", None):
        return jsonify({"error": "Invalid state parameter"}), 403

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    token_response = requests.post(
        OAUTH_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
        },
        headers={"Accept": "application/json"},
    )

    if token_response.status_code != 200:
        return jsonify({"error": "Token exchange failed", "status": token_response.status_code}), 502

    token_data = token_response.json()
    session["access_token"] = token_data.get("access_token")
    session["refresh_token"] = token_data.get("refresh_token")
    session["token_type"] = token_data.get("token_type", "Bearer")

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)