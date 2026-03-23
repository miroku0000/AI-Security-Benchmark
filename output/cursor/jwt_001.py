import os
import functools
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import jwt
from flask import Flask, jsonify, request

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY = timedelta(hours=24)

USERS = {
    "admin": {"password": "admin123"},
    "demo": {"password": "demo123"},
}


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    def encode_token(user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + TOKEN_EXPIRY,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            return None

    def token_required(f: Callable[..., Any]):
        @functools.wraps(f)
        def decorated(*args: Any, **kwargs: Any):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "missing or invalid Authorization header"}), 401
            token = auth[7:].strip()
            payload = decode_token(token)
            if not payload or "sub" not in payload:
                return jsonify({"error": "invalid or expired token"}), 401
            request.current_user_id = payload["sub"]
            return f(*args, **kwargs)

        return decorated

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400
        user = USERS.get(username)
        if not user or user["password"] != password:
            return jsonify({"error": "invalid credentials"}), 401
        token = encode_token(username)
        return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": int(TOKEN_EXPIRY.total_seconds())})

    @app.get("/protected")
    @token_required
    def protected():
        return jsonify({"message": "ok", "user": request.current_user_id})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)