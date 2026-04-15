import logging
import uuid
import time
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, g, jsonify

app = Flask(__name__)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

SENSITIVE_FIELDS = {"password", "token", "access_token", "refresh_token",
                    "authorization", "secret", "api_key", "credit_card"}


def redact_dict(data, depth=0):
    """Redact sensitive fields from a dictionary for safe logging."""
    if depth > 10 or not isinstance(data, dict):
        return data
    redacted = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, depth + 1)
        else:
            redacted[key] = value
    return redacted


def redact_headers(headers):
    """Redact sensitive headers for safe logging."""
    safe = {}
    for key, value in headers:
        if key.lower() in {"authorization", "cookie", "x-api-key"}:
            safe[key] = "***REDACTED***"
        else:
            safe[key] = value
    return safe


@app.before_request
def log_request():
    g.request_id = str(uuid.uuid4())
    g.start_time = time.monotonic()

    body = None
    if request.is_json:
        body = redact_dict(request.get_json(silent=True) or {})
    elif request.form:
        body = redact_dict(dict(request.form))

    app.logger.info(
        "REQUEST [%s] %s %s | remote=%s headers=%s body=%s",
        g.request_id,
        request.method,
        request.path,
        request.remote_addr,
        redact_headers(request.headers),
        body,
    )


@app.after_request
def log_response(response):
    duration_ms = (time.monotonic() - g.get("start_time", 0)) * 1000
    app.logger.info(
        "RESPONSE [%s] %s %s | status=%d duration=%.1fms",
        g.get("request_id", "?"),
        request.method,
        request.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.errorhandler(Exception)
def handle_error(exc):
    app.logger.error(
        "ERROR [%s] %s %s | error=%s",
        g.get("request_id", "?"),
        request.method,
        request.path,
        str(exc),
        exc_info=True,
    )
    return jsonify({"error": "Internal server error"}), 500


# --- Demo routes ---

USERS_DB = {
    "alice": {"password_hash": "hashed_pw_alice", "role": "admin"},
    "bob": {"password_hash": "hashed_pw_bob", "role": "user"},
}


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        app.logger.warning("Login attempt with missing credentials, user=%s", username)
        return jsonify({"error": "Username and password required"}), 400

    user = USERS_DB.get(username)
    if not user:
        app.logger.warning("Login failed: unknown user=%s", username)
        return jsonify({"error": "Invalid credentials"}), 401

    # In production, compare hashed passwords
    app.logger.info("Login succeeded for user=%s role=%s", username, user["role"])
    return jsonify({"message": "Login successful", "user": username, "role": user["role"]})


@app.route("/data", methods=["GET"])
def get_data():
    return jsonify({"items": [{"id": 1, "value": "example"}]})


@app.route("/data", methods=["POST"])
def create_data():
    data = request.get_json(force=True, silent=True) or {}
    app.logger.info("Creating data item: %s", redact_dict(data))
    return jsonify({"created": True, "item": data}), 201


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    app.run(debug=False, port=5000)