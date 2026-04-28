import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    try:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid token encoding") from exc


class JWTAuth:
    def __init__(self, secret_key: str, expiry_minutes: int = 60):
        self.secret_key = secret_key.encode("utf-8")
        self.expiry_minutes = expiry_minutes

    def generate_token(self, subject: str) -> str:
        now = datetime.now(timezone.utc)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.expiry_minutes)).timestamp()),
        }

        header_b64 = _b64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(
            self.secret_key, signing_input, hashlib.sha256
        ).digest()

        return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"

    def decode_token(self, token: str) -> dict:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:
            raise ValueError("Invalid token format") from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_signature = hmac.new(
            self.secret_key, signing_input, hashlib.sha256
        ).digest()
        actual_signature = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("Invalid token signature")

        try:
            header = json.loads(_b64url_decode(header_b64))
            payload = json.loads(_b64url_decode(payload_b64))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Invalid token payload") from exc

        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("Invalid token header")

        subject = payload.get("sub")
        issued_at = payload.get("iat")
        expires_at = payload.get("exp")

        if not isinstance(subject, str) or not subject:
            raise ValueError("Invalid token subject")
        if not isinstance(issued_at, int) or not isinstance(expires_at, int):
            raise ValueError("Invalid token timestamps")

        now = int(datetime.now(timezone.utc).timestamp())
        if expires_at <= now:
            raise ValueError("Token has expired")

        return payload

    @staticmethod
    def _unauthorized(message: str):
        response = jsonify({"error": message})
        response.status_code = 401
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    def required(self, view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            scheme, _, token = auth_header.partition(" ")

            if scheme.lower() != "bearer" or not token:
                return self._unauthorized("Missing or invalid Authorization header")

            try:
                payload = self.decode_token(token)
            except ValueError as exc:
                return self._unauthorized(str(exc))

            g.current_user = payload["sub"]
            g.jwt_payload = payload
            return view_func(*args, **kwargs)

        return wrapped


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        JWT_EXPIRY_MINUTES=int(os.environ.get("JWT_EXPIRY_MINUTES", "60")),
        DATABASE=os.environ.get("DATABASE", "auth.db"),
    )
    if config:
        app.config.update(config)

    auth = JWTAuth(
        secret_key=app.config["SECRET_KEY"],
        expiry_minutes=app.config["JWT_EXPIRY_MINUTES"],
    )

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    def init_db() -> None:
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()

    @app.teardown_appcontext
    def close_db(_error=None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.post("/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))

        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,150}", username):
            return jsonify(
                {
                    "error": "username must be 3-150 characters and contain only letters, numbers, ., _, or -"
                }
            ), 400

        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400

        try:
            db = get_db()
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "user already exists"}), 409

        return jsonify({"message": "user created"}), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))

        db = get_db()
        user = db.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "invalid credentials"}), 401

        token = auth.generate_token(user["username"])
        return jsonify(
            {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": app.config["JWT_EXPIRY_MINUTES"] * 60,
            }
        )

    @app.get("/me")
    @auth.required
    def me():
        return jsonify({"username": g.current_user})

    @app.get("/protected")
    @auth.required
    def protected():
        return jsonify({"message": f"Hello, {g.current_user}!"})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    with app.app_context():
        init_db()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_RUN_PORT", "5000")),
        debug=False,
    )