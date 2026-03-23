# -*- coding: utf-8 -*-
import os
import re
from datetime import timedelta
from functools import wraps

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(days=7)

_users = {
    "1": {
        "email": "user@example.com",
        "password_hash": generate_password_hash("oldpassword"),
        "two_factor_enabled": False,
    }
}


def login_required_json(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        uid = session.get("user_id")
        if not uid or uid not in _users:
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


def _valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if username == "demo" and password == "oldpassword":
        session["user_id"] = "1"
        session.permanent = True
        return jsonify({"ok": True, "user_id": "1"})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/profile", methods=["POST"])
@login_required_json
def update_profile():
    uid = session["user_id"]
    user = _users[uid]
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    if "email" in data:
        email = data["email"]
        if not isinstance(email, str) or not _valid_email(email):
            return jsonify({"error": "Invalid email"}), 400
        user["email"] = email.strip()

    if "new_password" in data or "current_password" in data:
        new_pw = data.get("new_password")
        cur_pw = data.get("current_password")
        if not cur_pw or not isinstance(cur_pw, str):
            return jsonify({"error": "current_password required"}), 400
        if not new_pw or not isinstance(new_pw, str):
            return jsonify({"error": "new_password required"}), 400
        if len(new_pw) < 8:
            return jsonify({"error": "new_password must be at least 8 characters"}), 400
        if not check_password_hash(user["password_hash"], cur_pw):
            return jsonify({"error": "Current password is incorrect"}), 401
        user["password_hash"] = generate_password_hash(new_pw)

    if "two_factor_enabled" in data:
        t = data["two_factor_enabled"]
        if not isinstance(t, bool):
            return jsonify({"error": "two_factor_enabled must be a boolean"}), 400
        user["two_factor_enabled"] = t

    return jsonify(
        {
            "email": user["email"],
            "two_factor_enabled": user["two_factor_enabled"],
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
