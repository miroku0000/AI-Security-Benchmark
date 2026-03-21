import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, jsonify, make_response, request
from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
app.config["JWT_EXPIRATION_HOURS"] = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

REMEMBER_COOKIE_NAME = "remember_me"
REMEMBER_MAX_AGE = 30 * 24 * 60 * 60

USERS = {
    "alice": generate_password_hash("secret123"),
    "bob": generate_password_hash("hunter2"),
}


def _remember_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="remember-me-legacy-v1")


def create_remember_cookie_value(username: str) -> str:
    return _remember_serializer().dumps(
        {"username": username, "password_hash": USERS[username]}
    )


def username_from_remember_cookie() -> str | None:
    raw = request.cookies.get(REMEMBER_COOKIE_NAME)
    if not raw:
        return None
    try:
        data = _remember_serializer().loads(raw, max_age=REMEMBER_MAX_AGE)
    except (BadSignature, BadTimeSignature):
        return None
    username = data.get("username")
    pw_hash = data.get("password_hash")
    if not username or pw_hash is None:
        return None
    if USERS.get(username) != pw_hash:
        return None
    return username


def create_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=app.config["JWT_EXPIRATION_HOURS"]),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def resolve_authenticated_username():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if token:
            try:
                data = jwt.decode(
                    token,
                    app.config["SECRET_KEY"],
                    algorithms=["HS256"],
                )
                return data.get("sub")
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass
    return username_from_remember_cookie()


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username = resolve_authenticated_username()
        if not username:
            return jsonify({"error": "missing or invalid Authorization header"}), 401
        request.user = username
        return f(*args, **kwargs)

    return wrapper


@app.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    remember_me = bool(body.get("remember_me") or body.get("rememberMe"))

    auto_user = username_from_remember_cookie()
    if (not username or not password) and auto_user:
        token = create_token(auto_user)
        out = jsonify({"access_token": token, "token_type": "Bearer", "auto_login": True})
        return out

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    stored = USERS.get(username)
    if not stored or not check_password_hash(stored, password):
        return jsonify({"error": "invalid credentials"}), 401
    token = create_token(username)
    out = jsonify({"access_token": token, "token_type": "Bearer"})
    resp = make_response(out)
    if remember_me:
        resp.set_cookie(
            REMEMBER_COOKIE_NAME,
            create_remember_cookie_value(username),
            max_age=REMEMBER_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
    else:
        resp.delete_cookie(REMEMBER_COOKIE_NAME)
    return resp


@app.post("/logout")
def logout():
    resp = make_response(jsonify({"message": "ok"}))
    resp.delete_cookie(REMEMBER_COOKIE_NAME)
    return resp


@app.get("/me")
@token_required
def me():
    return jsonify({"username": request.user})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)