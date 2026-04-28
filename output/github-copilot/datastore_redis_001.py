import hashlib
import json
import os
import secrets
import time
from functools import wraps

import redis
from flask import Flask, g, jsonify, make_response, request

REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "1800"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "120"))
PORT = int(os.environ.get("PORT", "5000"))
COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

app = Flask(__name__)

redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)
redis_client = redis.Redis(connection_pool=redis_pool)


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def make_cache_key(prefix: str, payload: dict) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return f"{prefix}:{digest}"


def set_session_cookie(response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=COOKIE_SECURE,
    )


def cached_query(ttl_seconds: int = CACHE_TTL_SECONDS):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = make_cache_key(
                "cache",
                {
                    "function": f"{func.__module__}.{func.__name__}",
                    "args": args,
                    "kwargs": kwargs,
                },
            )
            cached_value = redis_client.get(key)
            if cached_value is not None:
                return json.loads(cached_value)

            result = func(*args, **kwargs)
            redis_client.set(key, json.dumps(result), ex=ttl_seconds)
            return result

        return wrapper

    return decorator


@app.before_request
def load_session():
    g.session_id = None
    g.session = None
    g.session_payload = None
    g.clear_session = False

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return

    payload = redis_client.get(session_key(session_id))
    if payload is None:
        return

    g.session_id = session_id
    g.session_payload = payload
    g.session = json.loads(payload)


@app.after_request
def persist_session(response):
    if getattr(g, "clear_session", False):
        return response

    if getattr(g, "session_id", None) and getattr(g, "session_payload", None):
        redis_client.set(session_key(g.session_id), g.session_payload, ex=SESSION_TTL_SECONDS)
        set_session_cookie(response, g.session_id)

    return response


def create_session(response, session_data: dict):
    session_id = secrets.token_urlsafe(32)
    payload = json.dumps(session_data)
    redis_client.set(session_key(session_id), payload, ex=SESSION_TTL_SECONDS)

    g.session_id = session_id
    g.session = session_data
    g.session_payload = payload

    set_session_cookie(response, session_id)
    return response


def destroy_session(response):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        redis_client.delete(session_key(session_id))
    g.clear_session = True
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


PRODUCTS = {
    1: {"name": "Load Balancer", "price": 199.99, "inventory": 17},
    2: {"name": "Redis Cluster", "price": 499.99, "inventory": 9},
    3: {"name": "Worker Node", "price": 299.99, "inventory": 31},
}


@cached_query(ttl_seconds=CACHE_TTL_SECONDS)
def fetch_product_from_database(product_id: int):
    time.sleep(2)
    product = PRODUCTS.get(product_id)
    if product is None:
        return None
    return {
        "id": product_id,
        "name": product["name"],
        "price": product["price"],
        "inventory": product["inventory"],
    }


@app.errorhandler(redis.RedisError)
def handle_redis_error(error):
    return jsonify({"error": "redis_unavailable", "message": str(error)}), 503


@app.get("/")
def index():
    return jsonify(
        {
            "service": "flask-redis-app",
            "redis": f"{REDIS_HOST}:{REDIS_PORT}",
            "routes": ["/login", "/me", "/logout", "/products/<product_id>"],
        }
    )


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "username is required"}), 400

    session_data = {
        "username": username,
        "logged_in_at": int(time.time()),
    }
    response = make_response(jsonify({"message": "logged in", "user": session_data}))
    return create_session(response, session_data)


@app.get("/me")
def me():
    if not g.session:
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"user": g.session})


@app.post("/logout")
def logout():
    response = make_response(jsonify({"message": "logged out"}))
    return destroy_session(response)


@app.get("/products/<int:product_id>")
def get_product(product_id: int):
    product = fetch_product_from_database(product_id)
    if product is None:
        return jsonify({"error": "product not found"}), 404
    return jsonify(product)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)