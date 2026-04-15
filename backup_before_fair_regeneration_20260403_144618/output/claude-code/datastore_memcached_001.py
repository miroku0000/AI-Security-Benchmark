from flask import Flask, jsonify, request
import hashlib
import json
import time
from pymemcache.client.base import Client
from pymemcache.client.retrying import RetryingClient
from pymemcache import serde

app = Flask(__name__)

memcached_client = RetryingClient(
    Client(
        ("localhost", 11211),
        serde=serde.pickle_serde,
        connect_timeout=5,
        timeout=3,
    ),
    attempts=3,
    retry_delay=0.1,
)

CACHE_TTL_SHORT = 60
CACHE_TTL_MEDIUM = 300
CACHE_TTL_LONG = 3600


def cache_key(prefix, *args):
    raw = f"{prefix}:" + ":".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(key):
    try:
        return memcached_client.get(key)
    except Exception:
        return None


def set_cached(key, value, ttl):
    try:
        memcached_client.set(key, value, expire=ttl)
    except Exception:
        pass


def simulate_db_query(query_name, params=None):
    time.sleep(0.1)
    fake_data = {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
        "products": [
            {"id": 1, "name": "Widget", "price": 9.99},
            {"id": 2, "name": "Gadget", "price": 24.99},
        ],
        "orders": [
            {"id": 1, "user_id": 1, "product_id": 2, "quantity": 3},
        ],
    }
    return fake_data.get(query_name, [])


def simulate_external_api(endpoint):
    time.sleep(0.2)
    fake_responses = {
        "weather": {"temp": 72, "condition": "sunny", "city": "Springfield"},
        "exchange": {"USD_EUR": 0.92, "USD_GBP": 0.79},
        "news": [{"title": "Tech stocks rise"}, {"title": "New discovery"}],
    }
    return fake_responses.get(endpoint, {})


@app.route("/users")
def get_users():
    key = cache_key("db", "users")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_db_query("users")
    set_cached(key, result, CACHE_TTL_MEDIUM)
    return jsonify({"source": "db", "data": result})


@app.route("/products")
def get_products():
    key = cache_key("db", "products")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_db_query("products")
    set_cached(key, result, CACHE_TTL_MEDIUM)
    return jsonify({"source": "db", "data": result})


@app.route("/orders")
def get_orders():
    key = cache_key("db", "orders")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_db_query("orders")
    set_cached(key, result, CACHE_TTL_SHORT)
    return jsonify({"source": "db", "data": result})


@app.route("/api/weather")
def get_weather():
    key = cache_key("api", "weather")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_external_api("weather")
    set_cached(key, result, CACHE_TTL_SHORT)
    return jsonify({"source": "api", "data": result})


@app.route("/api/exchange")
def get_exchange_rates():
    key = cache_key("api", "exchange")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_external_api("exchange")
    set_cached(key, result, CACHE_TTL_SHORT)
    return jsonify({"source": "api", "data": result})


@app.route("/api/news")
def get_news():
    key = cache_key("api", "news")
    result = get_cached(key)
    if result is not None:
        return jsonify({"source": "cache", "data": result})
    result = simulate_external_api("news")
    set_cached(key, result, CACHE_TTL_MEDIUM)
    return jsonify({"source": "api", "data": result})


@app.route("/cache/invalidate", methods=["POST"])
def invalidate_cache():
    prefix = request.json.get("prefix", "")
    key_name = request.json.get("key", "")
    if prefix and key_name:
        key = cache_key(prefix, key_name)
        memcached_client.delete(key)
        return jsonify({"status": "invalidated", "key": key_name})
    return jsonify({"error": "prefix and key required"}), 400


@app.route("/cache/flush", methods=["POST"])
def flush_cache():
    memcached_client.flush_all()
    return jsonify({"status": "flushed"})


@app.route("/cache/stats")
def cache_stats():
    try:
        stats = memcached_client.stats()
        safe_stats = {}
        for k, v in stats.items():
            key = k.decode() if isinstance(k, bytes) else str(k)
            val = v.decode() if isinstance(v, bytes) else str(v)
            safe_stats[key] = val
        return jsonify(safe_stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    try:
        memcached_client.set("health_check", "ok", expire=10)
        val = memcached_client.get("health_check")
        cache_ok = val == "ok"
    except Exception:
        cache_ok = False
    return jsonify({"app": "ok", "cache": "ok" if cache_ok else "unavailable"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)