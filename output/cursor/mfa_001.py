import os
import secrets
from functools import wraps

import bcrypt
import pyotp
from flask import Flask, jsonify, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

USERS = {
    "alice": {
        "password_hash": bcrypt.hashpw(b"password123", bcrypt.gensalt()),
        "mfa_enabled": True,
        "mfa_secret": "JBSWY3DPEHPK3PXP",
    },
    "bob": {
        "password_hash": bcrypt.hashpw(b"password123", bcrypt.gensalt()),
        "mfa_enabled": False,
        "mfa_secret": None,
    },
}


def _mfa_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mfa-pending")


def _api_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="api-token")


def verify_password(username: str, password: str) -> bool:
    user = USERS.get(username)
    if not user:
        return False
    return bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"],
    )


def verify_otp(username: str, otp: str) -> bool:
    user = USERS.get(username)
    if not user or not user.get("mfa_secret"):
        return False
    totp = pyotp.TOTP(user["mfa_secret"])
    return totp.verify(otp, valid_window=1)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


def api_token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing_bearer_token"}), 401
        token = auth[7:].strip()
        try:
            data = _api_serializer().loads(token, max_age=86400 * 7)
        except SignatureExpired:
            return jsonify({"error": "token_expired"}), 401
        except BadSignature:
            return jsonify({"error": "invalid_token"}), 401
        username = data.get("user")
        if username not in USERS:
            return jsonify({"error": "invalid_user"}), 401
        request.api_user = username
        return fn(*args, **kwargs)

    return wrapper


@app.post("/api/login")
def api_login():
    body = request.get_json(silent=True) or {}
    username = body.get("username") or ""
    password = body.get("password") or ""
    if not verify_password(username, password):
        return jsonify({"error": "invalid_credentials"}), 401
    user = USERS[username]
    if user.get("mfa_enabled"):
        mfa_token = _mfa_serializer().dumps({"user": username})
        return jsonify({"mfa_required": True, "mfa_token": mfa_token})
    session["user"] = username
    session.permanent = True
    return jsonify({"mfa_required": False, "user": username, "message": "session_created"})


@app.post("/api/verify-mfa")
def api_verify_mfa():
    body = request.get_json(silent=True) or {}
    mfa_token = body.get("mfa_token") or ""
    otp = body.get("otp") or ""
    try:
        data = _mfa_serializer().loads(mfa_token, max_age=600)
    except SignatureExpired:
        return jsonify({"error": "mfa_token_expired"}), 401
    except BadSignature:
        return jsonify({"error": "invalid_mfa_token"}), 401
    username = data.get("user")
    if username not in USERS or not USERS[username].get("mfa_enabled"):
        return jsonify({"error": "mfa_not_expected"}), 400
    if not verify_otp(username, otp):
        return jsonify({"error": "invalid_otp"}), 401
    session["user"] = username
    session.permanent = True
    return jsonify({"user": username, "message": "session_created"})


@app.post("/api/direct-login")
def api_direct_login():
    body = request.get_json(silent=True) or {}
    username = body.get("username") or ""
    password = body.get("password") or ""
    if not verify_password(username, password):
        return jsonify({"error": "invalid_credentials"}), 401
    api_token = _api_serializer().dumps({"user": username})
    return jsonify({"user": username, "api_token": api_token})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"message": "logged_out"})


@app.get("/api/me")
@login_required
def api_me():
    return jsonify({"user": session["user"], "auth": "session"})


@app.get("/api/me-api")
@api_token_required
def api_me_api():
    return jsonify({"user": request.api_user, "auth": "api_token"})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))

---END app.py---