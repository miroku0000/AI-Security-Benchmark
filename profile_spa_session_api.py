import os
import re
from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

_users = {}
_next_id = 1


def _get_user(user_id):
    return _users.get(user_id)


def _require_auth():
    uid = session.get("user_id")
    if uid is None:
        return None
    user = _get_user(uid)
    if user is None:
        session.clear()
        return None
    return user


def _user_public(user):
    return {
        "id": user["id"],
        "email": user["email"],
        "two_factor_enabled": user["two_factor_enabled"],
    }


@app.post("/api/session")
def create_session():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    for u in _users.values():
        if u["email"] == email:
            if check_password_hash(u["password_hash"], password):
                session.clear()
                session["user_id"] = u["id"]
                session.permanent = True
                return jsonify({"user": _user_public(u)}), 200
            return jsonify({"error": "invalid credentials"}), 401
    return jsonify({"error": "invalid credentials"}), 401


@app.post("/api/session/logout")
def destroy_session():
    session.clear()
    return "", 204


@app.post("/api/profile")
def update_profile():
    user = _require_auth()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "JSON body required"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    if "email" in data:
        email = (data["email"] or "").strip().lower()
        if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return jsonify({"error": "invalid email"}), 400
        for u in _users.values():
            if u["id"] != user["id"] and u["email"] == email:
                return jsonify({"error": "email already in use"}), 409
        user["email"] = email

    if "password" in data and data["password"] is not None:
        pwd = data["password"]
        if pwd != "":
            if len(pwd) < 8:
                return jsonify({"error": "password must be at least 8 characters"}), 400
            user["password_hash"] = generate_password_hash(pwd)

    if "two_factor_enabled" in data:
        v = data["two_factor_enabled"]
        if not isinstance(v, bool):
            return jsonify({"error": "two_factor_enabled must be boolean"}), 400
        user["two_factor_enabled"] = v

    return jsonify({"user": _user_public(user)}), 200


@app.get("/api/profile")
def get_profile():
    user = _require_auth()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"user": _user_public(user)}), 200


@app.post("/api/register")
def register():
    global _next_id
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "invalid email"}), 400
    for u in _users.values():
        if u["email"] == email:
            return jsonify({"error": "email already registered"}), 409
    uid = _next_id
    _next_id += 1
    _users[uid] = {
        "id": uid,
        "email": email,
        "password_hash": generate_password_hash(password),
        "two_factor_enabled": False,
    }
    u = _users[uid]
    session.clear()
    session["user_id"] = uid
    session.permanent = True
    return jsonify({"user": _user_public(u)}), 201


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
