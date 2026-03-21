import datetime
import functools
import os

import jwt
from flask import Flask, jsonify, request

app = Flask(__name__)
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
USERS = {"admin": "secret", "user": "password123"}


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token() -> dict | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        data = verify_token()
        if data is None:
            return jsonify({"error": "unauthorized"}), 401
        request.auth_user = data.get("sub")
        return f(*args, **kwargs)

    return wrapper


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if USERS.get(username) != password:
        return jsonify({"error": "invalid credentials"}), 401
    token = create_token(username)
    return jsonify({"token": token})


@app.get("/protected")
@require_auth
def protected():
    return jsonify({"message": "ok", "user": request.auth_user})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
