import os
import time
from functools import wraps
from typing import Any, Dict, Optional

import jwt
from flask import Flask, jsonify, request

app = Flask(__name__)
SECRET = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 3600

USERS = {"alice": "secret123", "bob": "hunter2"}


def create_token(subject: str) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth[7:].strip()
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.jwt_subject = payload.get("sub")
        return f(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_token(username)
    return jsonify({"access_token": token, "token_type": "Bearer"})


@app.route("/protected", methods=["GET"])
@jwt_required
def protected():
    return jsonify({"message": "ok", "user": request.jwt_subject})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
