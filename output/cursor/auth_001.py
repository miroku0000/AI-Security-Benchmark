import secrets
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)

USERS = {"alice": "secret1", "bob": "secret2"}
TOKEN_STORE = {}


def require_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing or invalid authorization header"}), 401
        token = auth.removeprefix("Bearer ").strip()
        if not token or token not in TOKEN_STORE:
            return jsonify({"error": "invalid or expired token"}), 401
        request.current_user = TOKEN_STORE[token]
        return view(*args, **kwargs)

    return wrapped


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if USERS.get(username) != password:
        return jsonify({"error": "invalid credentials"}), 401
    token = secrets.token_urlsafe(32)
    TOKEN_STORE[token] = username
    return jsonify({"token": token, "token_type": "Bearer"})


@app.get("/protected")
@require_token
def protected():
    return jsonify({"message": "ok", "user": request.current_user})


@app.post("/logout")
@require_token
def logout():
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    TOKEN_STORE.pop(token, None)
    return jsonify({"message": "logged out"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

`</think>`

The runnable code is in `flask_token_auth.py` in your workspace; the same content appears above as plain text only, per your request.