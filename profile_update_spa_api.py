import os
import re
from functools import wraps

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

_USERS = {
    1: {
        "id": 1,
        "email": "user@example.com",
        "password_hash": generate_password_hash("correct-horse-battery-staple"),
        "two_factor_enabled": False,
    }
}


def _email_ok(value):
    if not value or not isinstance(value, str):
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value.strip()))


def session_auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")
        if not uid or uid not in _USERS:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, user=_USERS[uid], **kwargs)

    return wrapper


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    for u in _USERS.values():
        if u["email"].lower() == email and check_password_hash(u["password_hash"], password):
            session.clear()
            session["user_id"] = u["id"]
            session.permanent = bool(data.get("remember_me"))
            return jsonify(
                {
                    "id": u["id"],
                    "email": u["email"],
                    "two_factor_enabled": u["two_factor_enabled"],
                }
            ), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return "", 204


@app.route("/api/profile", methods=["POST"])
@session_auth_required
def update_profile(user):
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Expected JSON body"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON object"}), 400

    updated = {}

    if "email" in data:
        new_email = (data.get("email") or "").strip()
        if not _email_ok(new_email):
            return jsonify({"error": "Invalid email"}), 400
        user["email"] = new_email
        updated["email"] = user["email"]

    if "password" in data:
        current = data.get("current_password") or ""
        if not check_password_hash(user["password_hash"], current):
            return jsonify({"error": "Current password required or incorrect"}), 401
        new_pw = data.get("password") or ""
        if len(new_pw) < 10:
            return jsonify({"error": "Password must be at least 10 characters"}), 400
        user["password_hash"] = generate_password_hash(new_pw)
        updated["password"] = "changed"

    if "two_factor_enabled" in data:
        t = data["two_factor_enabled"]
        if not isinstance(t, bool):
            return jsonify({"error": "two_factor_enabled must be a boolean"}), 400
        user["two_factor_enabled"] = t
        updated["two_factor_enabled"] = user["two_factor_enabled"]

    if not updated:
        return jsonify({"error": "No recognized fields to update"}), 400

    return (
        jsonify(
            {
                "id": user["id"],
                "email": user["email"],
                "two_factor_enabled": user["two_factor_enabled"],
                "updated": updated,
            }
        ),
        200,
    )


@app.route("/api/session", methods=["GET"])
@session_auth_required
def session_status(user):
    return (
        jsonify(
            {
                "id": user["id"],
                "email": user["email"],
                "two_factor_enabled": user["two_factor_enabled"],
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
