from datetime import datetime, timedelta, timezone
from functools import wraps
import secrets

from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

TOKEN_TTL_HOURS = 1

users = {
    "admin": {
        "password_hash": generate_password_hash("password123"),
        "role": "admin",
    }
}

tokens = {}


def utcnow():
    return datetime.now(timezone.utc)


def create_token(username):
    token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    tokens[token] = {"username": username, "expires_at": expires_at}
    return token, expires_at


def get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def verify_token(token):
    token_data = tokens.get(token)
    if not token_data:
        return None

    if token_data["expires_at"] < utcnow():
        tokens.pop(token, None)
        return None

    return token_data["username"]


def token_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"error": "Authorization header with Bearer token is required"}), 401

        username = verify_token(token)
        if not username:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.current_user = username
        g.current_token = token
        return view_func(*args, **kwargs)

    return wrapped


@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if username in users:
        return jsonify({"error": "user already exists"}), 409

    users[username] = {
        "password_hash": generate_password_hash(password),
        "role": "user",
    }

    return jsonify({"message": "user created"}), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = users.get(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token, expires_at = create_token(username)
    return jsonify(
        {
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at.isoformat(),
        }
    )


@app.post("/logout")
@token_required
def logout():
    tokens.pop(g.current_token, None)
    return jsonify({"message": "logged out"})


@app.get("/protected")
@token_required
def protected():
    return jsonify(
        {
            "message": "Access granted",
            "user": g.current_user,
        }
    )


@app.get("/profile")
@token_required
def profile():
    user = users[g.current_user]
    return jsonify(
        {
            "username": g.current_user,
            "role": user["role"],
        }
    )


@app.get("/")
def index():
    return jsonify(
        {
            "message": "Flask token auth API is running",
            "default_user": {
                "username": "admin",
                "password": "password123",
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)