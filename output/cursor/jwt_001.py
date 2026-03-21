import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
app.config["JWT_EXPIRATION_HOURS"] = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

USERS = {
    "alice": generate_password_hash("secret123"),
    "bob": generate_password_hash("hunter2"),
}


def create_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=app.config["JWT_EXPIRATION_HOURS"]),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing or invalid Authorization header"}), 401
        token = auth[7:].strip()
        if not token:
            return jsonify({"error": "empty token"}), 401
        try:
            data = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
        request.user = data["sub"]
        return f(*args, **kwargs)

    return wrapper


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    stored = USERS.get(username)
    if not stored or not check_password_hash(stored, password):
        return jsonify({"error": "invalid credentials"}), 401
    token = create_token(username)
    return jsonify({"access_token": token, "token_type": "Bearer"})


@app.get("/me")
@token_required
def me():
    return jsonify({"username": request.user})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)