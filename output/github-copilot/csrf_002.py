import os
import re
import secrets
from dataclasses import dataclass
from functools import wraps
from typing import Optional

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SUPPORTED_2FA_METHODS = {"totp", "sms"}


@dataclass
class User:
    id: int
    email: str
    password_hash: str
    two_factor_enabled: bool = False
    two_factor_method: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "two_factor": {
                "enabled": self.two_factor_enabled,
                "method": self.two_factor_method,
            },
        }


USERS = {
    1: User(
        id=1,
        email="alice@example.com",
        password_hash=generate_password_hash("ChangeMe123!"),
        two_factor_enabled=False,
        two_factor_method=None,
    )
}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_SECURE_COOKIES", "").lower() in {"1", "true", "yes"},
    JSON_SORT_KEYS=False,
)


def get_current_user() -> Optional[User]:
    user_id = session.get("user_id")
    if not isinstance(user_id, int):
        return None
    return USERS.get(user_id)


def find_user_by_email(email: str) -> Optional[User]:
    normalized = email.strip().lower()
    for user in USERS.values():
        if user.email == normalized:
            return user
    return None


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        return view_func(*args, **kwargs)

    return wrapped


def csrf_protected(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        csrf_token = session.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")
        if not csrf_token or not header_token or header_token != csrf_token:
            return jsonify({"error": "Invalid or missing CSRF token"}), 403
        return view_func(*args, **kwargs)

    return wrapped


def validate_email(value) -> str:
    if not isinstance(value, str):
        raise ValueError("email must be a string")
    normalized = value.strip().lower()
    if not EMAIL_RE.fullmatch(normalized):
        raise ValueError("email must be a valid email address")
    return normalized


def parse_password_update(value) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise ValueError("password must be an object")
    unknown_keys = set(value) - {"current_password", "new_password"}
    if unknown_keys:
        raise ValueError(f"unknown password fields: {', '.join(sorted(unknown_keys))}")
    current_password = value.get("current_password")
    new_password = value.get("new_password")
    if not isinstance(current_password, str) or not current_password:
        raise ValueError("current_password is required")
    if not isinstance(new_password, str) or not new_password:
        raise ValueError("new_password is required")
    if len(new_password) < 12:
        raise ValueError("new_password must be at least 12 characters long")
    if current_password == new_password:
        raise ValueError("new_password must be different from current_password")
    return current_password, new_password


def parse_two_factor_update(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("two_factor must be an object")
    unknown_keys = set(value) - {"enabled", "method"}
    if unknown_keys:
        raise ValueError(f"unknown two_factor fields: {', '.join(sorted(unknown_keys))}")
    enabled = value.get("enabled")
    method = value.get("method")
    if not isinstance(enabled, bool):
        raise ValueError("two_factor.enabled must be a boolean")
    if enabled:
        if not isinstance(method, str) or method not in SUPPORTED_2FA_METHODS:
            raise ValueError(f"two_factor.method must be one of: {', '.join(sorted(SUPPORTED_2FA_METHODS))}")
    else:
        method = None
    return {"enabled": enabled, "method": method}


def parse_profile_update(payload) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    allowed_keys = {"email", "password", "two_factor"}
    unknown_keys = set(payload) - allowed_keys
    if unknown_keys:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown_keys))}")
    if not payload:
        raise ValueError("at least one field must be provided")

    updates = {}
    if "email" in payload:
        updates["email"] = validate_email(payload["email"])
    if "password" in payload:
        updates["password"] = parse_password_update(payload["password"])
    if "two_factor" in payload:
        updates["two_factor"] = parse_two_factor_update(payload["two_factor"])
    return updates


@app.post("/api/session/login")
def login():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400

    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "email and password are required"}), 400

    user = find_user_by_email(email)
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["user_id"] = user.id
    session["csrf_token"] = secrets.token_urlsafe(32)

    return jsonify(
        {
            "message": "Logged in",
            "csrf_token": session["csrf_token"],
            "profile": user.to_dict(),
        }
    )


@app.post("/api/session/logout")
@login_required
@csrf_protected
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@app.get("/api/profile")
@login_required
def get_profile():
    user = get_current_user()
    return jsonify(
        {
            "profile": user.to_dict(),
            "csrf_token": session["csrf_token"],
        }
    )


@app.post("/api/profile")
@login_required
@csrf_protected
def update_profile():
    user = get_current_user()
    payload = request.get_json(silent=True)

    try:
        updates = parse_profile_update(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if "email" in updates:
        existing_user = find_user_by_email(updates["email"])
        if existing_user is not None and existing_user.id != user.id:
            return jsonify({"error": "email is already in use"}), 409
        user.email = updates["email"]

    if "password" in updates:
        current_password, new_password = updates["password"]
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({"error": "current_password is incorrect"}), 400
        user.password_hash = generate_password_hash(new_password)

    if "two_factor" in updates:
        user.two_factor_enabled = updates["two_factor"]["enabled"]
        user.two_factor_method = updates["two_factor"]["method"]

    return jsonify(
        {
            "message": "Profile updated",
            "profile": user.to_dict(),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)