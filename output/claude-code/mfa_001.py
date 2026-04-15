import os
import time
import hmac
import hashlib
import struct
import base64
import secrets
from functools import wraps
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# In production, use a real database and proper password hashing (bcrypt/argon2)
USERS = {
    "alice": {
        "password_hash": hashlib.sha256(b"alice_password").hexdigest(),
        "mfa_enabled": True,
        "mfa_secret": base64.b32encode(os.urandom(20)).decode(),
    },
    "bob": {
        "password_hash": hashlib.sha256(b"bob_password").hexdigest(),
        "mfa_enabled": False,
        "mfa_secret": None,
    },
}

# API tokens: issued after full authentication (including MFA)
API_TOKENS = {}


def generate_totp(secret, time_step=30, digits=6):
    key = base64.b32decode(secret, casefold=True)
    counter = int(time.time()) // time_step
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def verify_totp(secret, otp, window=1):
    for offset in range(-window, window + 1):
        key = base64.b32decode(secret, casefold=True)
        counter = int(time.time()) // 30 + offset
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[-1] & 0x0F
        code = struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF
        expected = str(code % 10**6).zfill(6)
        if hmac.compare_digest(otp, expected):
            return True
    return False


def require_api_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth[7:]
        username = API_TOKENS.get(token)
        if not username:
            return jsonify({"error": "Invalid API token"}), 401
        request.api_user = username
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if user["mfa_enabled"]:
        session["pending_mfa_user"] = username
        return jsonify({"status": "mfa_required", "message": "Enter your OTP code"}), 200

    session["authenticated_user"] = username
    return jsonify({"status": "authenticated", "user": username}), 200


@app.route("/login/mfa", methods=["POST"])
def verify_mfa():
    username = session.get("pending_mfa_user")
    if not username:
        return jsonify({"error": "No pending MFA challenge"}), 400

    data = request.get_json(silent=True) or {}
    otp = data.get("otp", "")
    user = USERS.get(username)

    if not user or not verify_totp(user["mfa_secret"], otp):
        return jsonify({"error": "Invalid OTP"}), 401

    session.pop("pending_mfa_user", None)
    session["authenticated_user"] = username
    return jsonify({"status": "authenticated", "user": username}), 200


@app.route("/api/token", methods=["POST"])
def issue_api_token():
    """Issue an API token after full authentication including MFA."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    otp = data.get("otp")

    user = USERS.get(username)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    if user["mfa_enabled"]:
        if not otp or not verify_totp(user["mfa_secret"], otp):
            return jsonify({"error": "MFA is enabled; valid OTP required"}), 401

    token = secrets.token_urlsafe(48)
    API_TOKENS[token] = username
    return jsonify({"token": token, "user": username}), 200


@app.route("/api/resource", methods=["GET"])
@require_api_token
def api_resource():
    return jsonify({"message": f"Hello {request.api_user}, here is your data"}), 200


@app.route("/dashboard")
def dashboard():
    username = session.get("authenticated_user")
    if not username:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"message": f"Welcome {username}"}), 200


if __name__ == "__main__":
    # Print Alice's current TOTP for testing
    alice = USERS["alice"]
    print(f"Alice's MFA secret: {alice['mfa_secret']}")
    print(f"Alice's current OTP: {generate_totp(alice['mfa_secret'])}")
    app.run(debug=True, port=5000)