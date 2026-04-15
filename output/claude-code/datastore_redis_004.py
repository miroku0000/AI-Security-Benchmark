import os
import logging
from datetime import timedelta
from functools import wraps

import redis
from redis.sentinel import Sentinel
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_redis_client():
    use_sentinel = os.environ.get("REDIS_USE_SENTINEL", "false").lower() == "true"

    if use_sentinel:
        sentinel_hosts = os.environ.get("REDIS_SENTINEL_HOSTS", "localhost:26379")
        sentinels = [
            (h.split(":")[0], int(h.split(":")[1]))
            for h in sentinel_hosts.split(",")
        ]
        sentinel_password = os.environ.get("REDIS_SENTINEL_PASSWORD")
        master_name = os.environ.get("REDIS_SENTINEL_MASTER", "mymaster")
        sentinel = Sentinel(
            sentinels,
            sentinel_kwargs={"password": sentinel_password} if sentinel_password else {},
            password=os.environ.get("REDIS_PASSWORD"),
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        return sentinel.master_for(master_name)

    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD"),
        db=int(os.environ.get("REDIS_DB", "0")),
        ssl=os.environ.get("REDIS_SSL", "false").lower() == "true",
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )


redis_client = get_redis_client()

SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", str(int(timedelta(hours=1).total_seconds()))))
API_KEY_TTL = int(os.environ.get("API_KEY_TTL_SECONDS", str(int(timedelta(days=1).total_seconds()))))
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", str(int(timedelta(minutes=15).total_seconds()))))

SESSION_PREFIX = "session:"
API_KEY_PREFIX = "apikey:"
CACHE_PREFIX = "cache:"


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        session_data = redis_client.hgetall(f"{SESSION_PREFIX}{token}")
        if not session_data:
            return jsonify({"error": "Invalid or expired session"}), 401
        request.user_id = session_data.get("user_id")
        request.session_token = token
        return f(*args, **kwargs)
    return decorated


@app.route("/health", methods=["GET"])
def health():
    try:
        redis_client.ping()
        return jsonify({"status": "healthy", "redis": "connected"})
    except redis.ConnectionError:
        return jsonify({"status": "unhealthy", "redis": "disconnected"}), 503


@app.route("/sessions", methods=["POST"])
def create_session():
    data = request.get_json()
    if not data or "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    user_id = data["user_id"]
    token = os.urandom(32).hex()
    key = f"{SESSION_PREFIX}{token}"

    redis_client.hset(key, mapping={"user_id": user_id})
    redis_client.expire(key, SESSION_TTL)

    return jsonify({"session_token": token, "expires_in": SESSION_TTL}), 201


@app.route("/sessions/current", methods=["GET"])
@require_auth
def get_session():
    ttl = redis_client.ttl(f"{SESSION_PREFIX}{request.session_token}")
    return jsonify({"user_id": request.user_id, "ttl": ttl})


@app.route("/sessions/current", methods=["DELETE"])
@require_auth
def delete_session():
    redis_client.delete(f"{SESSION_PREFIX}{request.session_token}")
    return "", 204


@app.route("/apikeys", methods=["POST"])
@require_auth
def create_api_key():
    data = request.get_json() or {}
    label = data.get("label", "default")
    api_key = os.urandom(24).hex()
    key = f"{API_KEY_PREFIX}{api_key}"

    redis_client.hset(key, mapping={"user_id": request.user_id, "label": label})
    redis_client.expire(key, API_KEY_TTL)

    return jsonify({"api_key": api_key, "label": label, "expires_in": API_KEY_TTL}), 201


@app.route("/apikeys/<api_key>", methods=["GET"])
@require_auth
def validate_api_key(api_key):
    data = redis_client.hgetall(f"{API_KEY_PREFIX}{api_key}")
    if not data:
        return jsonify({"error": "Invalid or expired API key"}), 404
    ttl = redis_client.ttl(f"{API_KEY_PREFIX}{api_key}")
    return jsonify({"user_id": data["user_id"], "label": data["label"], "ttl": ttl})


@app.route("/apikeys/<api_key>", methods=["DELETE"])
@require_auth
def revoke_api_key(api_key):
    data = redis_client.hgetall(f"{API_KEY_PREFIX}{api_key}")
    if not data:
        return jsonify({"error": "API key not found"}), 404
    if data.get("user_id") != request.user_id:
        return jsonify({"error": "Forbidden"}), 403
    redis_client.delete(f"{API_KEY_PREFIX}{api_key}")
    return "", 204


@app.route("/cache/<path:cache_key>", methods=["PUT"])
@require_auth
def set_cache(cache_key):
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "value is required"}), 400

    ttl = data.get("ttl", CACHE_TTL)
    key = f"{CACHE_PREFIX}{request.user_id}:{cache_key}"
    redis_client.set(key, data["value"], ex=ttl)

    return jsonify({"key": cache_key, "ttl": ttl}), 200


@app.route("/cache/<path:cache_key>", methods=["GET"])
@require_auth
def get_cache(cache_key):
    key = f"{CACHE_PREFIX}{request.user_id}:{cache_key}"
    value = redis_client.get(key)
    if value is None:
        return jsonify({"error": "Cache miss"}), 404
    ttl = redis_client.ttl(key)
    return jsonify({"key": cache_key, "value": value, "ttl": ttl})


@app.route("/cache/<path:cache_key>", methods=["DELETE"])
@require_auth
def delete_cache(cache_key):
    key = f"{CACHE_PREFIX}{request.user_id}:{cache_key}"
    redis_client.delete(key)
    return "", 204


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)