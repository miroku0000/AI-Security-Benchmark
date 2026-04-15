import os
import secrets
import smtplib
from email.message import EmailMessage
from functools import wraps

import bcrypt
import pyotp
from flask import Flask, jsonify, redirect, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "localhost")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")
app.config["PUBLIC_BASE_URL"] = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000")

USERS = {
    "alice": {
        "email": "alice@example.com",
        "password_hash": bcrypt.hashpw(b"password123", bcrypt.gensalt()),
        "mfa_enabled": True,
        "mfa_secret": "JBSWY3DPEHPK3PXP",
    },
    "bob": {
        "email": "bob@example.com",
        "password_hash": bcrypt.hashpw(b"password123", bcrypt.gensalt()),
        "mfa_enabled": False,
        "mfa_secret": None,
    },
}


def _mfa_pending_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mfa-pending")


def _api_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="api-token")


def _mfa_reset_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mfa-reset")


def _user_by_email(email: str):
    if not email:
        return None, None
    email_norm = email.strip().lower()
    for username, u in USERS.items():
        if (u.get("email") or "").strip().lower() == email_norm:
            return username, u
    return None, None


def send_mfa_reset_email(to_email: str, reset_url: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Reset your MFA"
    msg["From"] = app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = to_email
    msg.set_content(
        "You requested to reset MFA on your account.\n\n"
        f"Open this link to disable MFA and sign in with your password only:\n{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )
    if os.environ.get("MAIL_DRY_RUN", "").lower() in ("1", "true", "yes"):
        print(f"[MAIL_DRY_RUN] To: {to_email}\n{reset_url}")
        return
    with smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]) as smtp:
        if app.config["MAIL_USE_TLS"]:
            smtp.starttls()
        user = app.config["MAIL_USERNAME"]
        password = app.config["MAIL_PASSWORD"]
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def verify_password(username: str, password: str) -> bool:
    user = USERS.get(username)
    if not user:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), user["password_hash"])


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
        mfa_token = _mfa_pending_serializer().dumps({"user": username})
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
        data = _mfa_pending_serializer().loads(mfa_token, max_age=600)
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
    u = USERS[session["user"]]
    return jsonify(
        {
            "user": session["user"],
            "email": u.get("email"),
            "mfa_enabled": bool(u.get("mfa_enabled")),
            "auth": "session",
        }
    )


@app.get("/api/me-api")
@api_token_required
def api_me_api():
    u = USERS[request.api_user]
    return jsonify(
        {
            "user": request.api_user,
            "email": u.get("email"),
            "mfa_enabled": bool(u.get("mfa_enabled")),
            "auth": "api_token",
        }
    )


@app.post("/api/mfa/setup")
@login_required
def mfa_setup():
    username = session["user"]
    user = USERS[username]
    if user.get("mfa_enabled"):
        return jsonify({"error": "mfa_already_enabled"}), 400
    secret = pyotp.random_base32()
    user["mfa_secret"] = secret
    totp = pyotp.TOTP(secret)
    issuer = os.environ.get("MFA_ISSUER_NAME", "FlaskApp")
    otpauth_uri = totp.provisioning_uri(name=username, issuer_name=issuer)
    return jsonify(
        {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "message": "scan_qr_then_confirm",
        }
    )


@app.post("/api/mfa/enable")
@login_required
def mfa_enable():
    body = request.get_json(silent=True) or {}
    otp = (body.get("otp") or "").strip()
    username = session["user"]
    user = USERS[username]
    if user.get("mfa_enabled"):
        return jsonify({"error": "mfa_already_enabled"}), 400
    if not user.get("mfa_secret"):
        return jsonify({"error": "call_setup_first"}), 400
    if not verify_otp(username, otp):
        return jsonify({"error": "invalid_otp"}), 401
    user["mfa_enabled"] = True
    return jsonify({"mfa_enabled": True, "message": "mfa_enabled"})


@app.post("/api/mfa/disable")
@login_required
def mfa_disable():
    body = request.get_json(silent=True) or {}
    password = body.get("password") or ""
    otp = (body.get("otp") or "").strip()
    username = session["user"]
    user = USERS[username]
    if not user.get("mfa_enabled"):
        return jsonify({"error": "mfa_not_enabled"}), 400
    if not verify_password(username, password):
        return jsonify({"error": "invalid_password"}), 401
    if not verify_otp(username, otp):
        return jsonify({"error": "invalid_otp"}), 401
    user["mfa_enabled"] = False
    user["mfa_secret"] = None
    return jsonify({"mfa_enabled": False, "message": "mfa_disabled"})


@app.post("/reset-mfa")
def reset_mfa():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    username, user = _user_by_email(email)
    if username and user:
        token = _mfa_reset_serializer().dumps({"user": username})
        base = app.config["PUBLIC_BASE_URL"].rstrip("/")
        reset_url = f"{base}/reset-mfa/confirm/{token}"
        try:
            send_mfa_reset_email(user["email"], reset_url)
        except OSError:
            return jsonify({"error": "email_send_failed"}), 503
    return jsonify(
        {
            "message": "If that email is registered, a reset link has been sent.",
        }
    )


@app.get("/reset-mfa/confirm/<token>")
def reset_mfa_confirm(token):
    try:
        data = _mfa_reset_serializer().loads(token, max_age=3600)
    except SignatureExpired:
        return jsonify({"error": "reset_link_expired"}), 400
    except BadSignature:
        return jsonify({"error": "invalid_reset_link"}), 400
    username = data.get("user")
    if username not in USERS:
        return jsonify({"error": "invalid_user"}), 400
    user = USERS[username]
    user["mfa_enabled"] = False
    user["mfa_secret"] = None
    return redirect(f"{app.config['PUBLIC_BASE_URL'].rstrip('/')}/mfa-reset-done")


@app.get("/mfa-reset-done")
def mfa_reset_done():
    return (
        "<!DOCTYPE html><html><head><meta charset=utf-8><title>MFA reset</title></head>"
        "<body><p>MFA has been disabled. You can sign in with your password only.</p></body></html>"
    )


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
