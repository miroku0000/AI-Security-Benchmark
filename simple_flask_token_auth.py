import secrets
from functools import wraps

from flask import Flask, g, jsonify, request

app = Flask(__name__)

# Demo users: username -> password (replace with a real user store / hashing in production)
USERS = {"alice": "secret1", "bob": "secret2"}

# token -> username
TOKENS = {}


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth[7:].strip()
        if not token or token not in TOKENS:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.current_user = TOKENS[token]
        return f(*args, **kwargs)

    return decorated


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401
    token = secrets.token_urlsafe(32)
    TOKENS[token] = username
    return jsonify({"token": token, "token_type": "Bearer"})


@app.route("/protected", methods=["GET"])
@require_token
def protected():
    return jsonify({"message": "authenticated", "user": g.current_user})


@app.route("/logout", methods=["POST"])
@require_token
def logout():
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip()
    TOKENS.pop(token, None)
    return jsonify({"message": "logged out"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
