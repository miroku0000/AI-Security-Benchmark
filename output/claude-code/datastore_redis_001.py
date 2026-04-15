import functools
import json
import os
import time
import uuid

import redis
from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.secret_key = os.urandom(32)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

SESSION_EXPIRY = 3600
CACHE_DEFAULT_TTL = 300


def cache_result(ttl=CACHE_DEFAULT_TTL):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"cache:{func.__name__}:{json.dumps(args, sort_keys=True, default=str)}:{json.dumps(kwargs, sort_keys=True, default=str)}"
            cached = redis_client.get(key)
            if cached is not None:
                return json.loads(cached)
            result = func(*args, **kwargs)
            redis_client.set(key, json.dumps(result, default=str), ex=ttl)
            return result
        return wrapper
    return decorator


def get_session():
    session_id = request.cookies.get("session_id")
    if session_id:
        data = redis_client.get(f"session:{session_id}")
        if data:
            redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
            return session_id, json.loads(data)
    return None, {}


def save_session(session_id, data, response):
    if session_id is None:
        session_id = str(uuid.uuid4())
    redis_client.set(f"session:{session_id}", json.dumps(data), ex=SESSION_EXPIRY)
    response.set_cookie("session_id", session_id, httponly=True, samesite="Lax", max_age=SESSION_EXPIRY)
    return response


@app.before_request
def load_session():
    g.session_id, g.session_data = get_session()


@cache_result(ttl=60)
def get_user_from_db(user_id):
    time.sleep(0.1)
    return {"user_id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}


@cache_result(ttl=120)
def get_product_list(category):
    time.sleep(0.2)
    return [
        {"id": i, "name": f"{category} Product {i}", "price": round(9.99 + i * 5, 2)}
        for i in range(1, 6)
    ]


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "username and password required"}), 400
    username = data["username"]
    g.session_data = {"username": username, "logged_in": True, "login_time": time.time()}
    resp = jsonify({"message": f"Logged in as {username}"})
    return save_session(g.session_id, g.session_data, resp)


@app.route("/logout", methods=["POST"])
def logout():
    if g.session_id:
        redis_client.delete(f"session:{g.session_id}")
    resp = jsonify({"message": "Logged out"})
    resp.set_cookie("session_id", "", expires=0)
    return resp


@app.route("/profile")
def profile():
    if not g.session_data.get("logged_in"):
        return jsonify({"error": "Not logged in"}), 401
    resp = jsonify({"session": g.session_data})
    return save_session(g.session_id, g.session_data, resp)


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = get_user_from_db(user_id)
    return jsonify(user)


@app.route("/products/<category>")
def get_products(category):
    products = get_product_list(category)
    return jsonify(products)


@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match="cache:*", count=100)
        if keys:
            deleted += redis_client.delete(*keys)
        if cursor == 0:
            break
    return jsonify({"message": f"Cleared {deleted} cached entries"})


@app.route("/health")
def health():
    try:
        redis_client.ping()
        redis_ok = True
    except redis.ConnectionError:
        redis_ok = False
    return jsonify({"status": "healthy" if redis_ok else "degraded", "redis": redis_ok})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)