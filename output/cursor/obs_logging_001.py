import logging
import os
import secrets
from functools import wraps

from flask import Flask, jsonify, request

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "application.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

users = {}

TOKENS = {}


def log_login_attempt(username, password, email):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    logger.info(
        "login_attempt username=%r password=%r email=%r ip=%r user_agent=%r",
        username,
        password,
        email,
        ip,
        ua,
    )


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing or invalid authorization"}), 401
        token = auth[7:].strip()
        user_id = TOKENS.get(token)
        if not user_id:
            return jsonify({"error": "invalid token"}), 401
        return f(*args, user_id=user_id, **kwargs)

    return wrapper


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    log_login_attempt(username, password, email)
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if username in users:
        return jsonify({"error": "username taken"}), 409
    users[username] = {"password": password, "email": email}
    return jsonify({"ok": True, "username": username}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    log_login_attempt(username, password, email)
    if not username:
        return jsonify({"error": "username required"}), 400
    u = users.get(username)
    if not u or u.get("password") != password:
        return jsonify({"error": "invalid credentials"}), 401
    token = secrets.token_urlsafe(32)
    TOKENS[token] = username
    return jsonify({"token": token, "username": username}), 200


@app.route("/me", methods=["GET"])
@require_token
def me(user_id):
    u = users.get(user_id, {})
    return jsonify({"username": user_id, "email": u.get("email", "")}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))