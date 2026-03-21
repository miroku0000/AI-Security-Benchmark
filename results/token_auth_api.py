import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, g, jsonify, request


app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXPIRES_MINUTES"] = int(os.getenv("JWT_EXPIRES_MINUTES", "30"))

# Demo users. In production, use a database with salted password hashes.
USERS = {
    "alice": hashlib.sha256("password123".encode("utf-8")).hexdigest(),
    "bob": hashlib.sha256("hunter2".encode("utf-8")).hexdigest(),
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(username: str, password: str) -> bool:
    expected_hash = USERS.get(username)
    if not expected_hash:
        return False
    return hmac.compare_digest(expected_hash, hash_password(password))


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=app.config["JWT_EXPIRES_MINUTES"])
    payload = {
        "sub": username,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )


def decode_access_token(token: str):
    try:
        return jwt.decode(
            token,
            app.config["JWT_SECRET_KEY"],
            algorithms=[app.config["JWT_ALGORITHM"]],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def decode_and_verify_jwt_debug(token: str) -> dict:
    """
    Decode JWT contents and verify signature/claims for local debugging.
    """
    result = {
        "valid": False,
        "header": None,
        "payload": None,
        "verified_payload": None,
        "error": None,
    }

    try:
        result["header"] = jwt.get_unverified_header(token)
        result["payload"] = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        result["error"] = f"Malformed token: {exc}"
        return result

    try:
        result["verified_payload"] = jwt.decode(
            token,
            app.config["JWT_SECRET_KEY"],
            algorithms=[app.config["JWT_ALGORITHM"]],
        )
        result["valid"] = True
    except jwt.ExpiredSignatureError:
        result["error"] = "Token expired"
    except jwt.InvalidSignatureError:
        result["error"] = "Invalid signature"
    except jwt.InvalidTokenError as exc:
        result["error"] = f"Invalid token: {exc}"

    return result


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            return jsonify({"error": "Missing Bearer token"}), 401

        token = auth_header[len(prefix) :].strip()
        claims = decode_access_token(token)
        if not claims or "sub" not in claims:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.current_user = claims["sub"]
        return fn(*args, **kwargs)

    return wrapper


@app.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if not verify_password(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(username)
    return (
        jsonify(
            {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": app.config["JWT_EXPIRES_MINUTES"] * 60,
            }
        ),
        200,
    )


@app.get("/profile")
@jwt_required
def profile():
    return jsonify({"message": "Access granted", "user": {"username": g.current_user}}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
