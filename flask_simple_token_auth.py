import os
from functools import wraps

from flask import Flask, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

USERS = {"admin": "secret123", "user": "pass456"}

_serializer = URLSafeTimedSerializer(
    app.config["SECRET_KEY"],
    salt="flask-simple-token-auth",
)


def token_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = header[7:].strip()
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = _serializer.loads(token, max_age=86400)
        except SignatureExpired:
            return jsonify({"error": "Token expired"}), 401
        except BadSignature:
            return jsonify({"error": "Invalid token"}), 401
        request.token_user = payload.get("sub")
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
        return jsonify({"error": "Invalid credentials"}), 401
    token = _serializer.dumps({"sub": username})
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 86400})


@app.get("/protected")
@token_required
def protected():
    return jsonify({"message": "ok", "user": request.token_user})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
