import secrets
from functools import wraps

from flask import Flask, g, jsonify, request

app = Flask(__name__)

USERS = {
    "admin": "secret",
    "alice": "password123",
}

TOKENS = {}


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing or invalid authorization header"}), 401
        token = auth[7:].strip()
        if not token or token not in TOKENS:
            return jsonify({"error": "invalid or expired token"}), 401
        g.current_user = TOKENS[token]
        return f(*args, **kwargs)

    return decorated


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if USERS.get(username) != password:
        return jsonify({"error": "invalid credentials"}), 401
    for existing, user in list(TOKENS.items()):
        if user == username:
            del TOKENS[existing]
    token = secrets.token_urlsafe(32)
    TOKENS[token] = username
    return jsonify({"token": token, "token_type": "Bearer"})


@app.get("/protected/profile")
@require_token
def profile():
    return jsonify({"username": g.current_user, "message": "authenticated"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
