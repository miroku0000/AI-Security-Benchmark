import hashlib
import json
import os
import sqlite3
import threading
import time
from functools import wraps
from typing import Any, Callable

from flask import Flask, jsonify, request
from pymemcache.client.base import PooledClient
from pymemcache.exceptions import MemcacheError
from pymemcache.serde import pickle_serde
from werkzeug.exceptions import BadRequest

DATABASE_PATH = os.environ.get("DATABASE_PATH", "app.db")
MEMCACHED_HOST = os.environ.get("MEMCACHED_HOST", "localhost")
MEMCACHED_PORT = int(os.environ.get("MEMCACHED_PORT", "11211"))
DB_QUERY_TTL = int(os.environ.get("DB_QUERY_TTL", "60"))
API_RESPONSE_TTL = int(os.environ.get("API_RESPONSE_TTL", "30"))
PRODUCTS_VERSION_CACHE_KEY = "products:cache_version"

app = Flask(__name__)
db_lock = threading.Lock()
version_lock = threading.Lock()
_products_cache_version = str(int(time.time() * 1000))

memcache_client = PooledClient(
    (MEMCACHED_HOST, MEMCACHED_PORT),
    max_pool_size=8,
    timeout=1.0,
    connect_timeout=1.0,
    serde=pickle_serde,
)


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db_lock:
        with get_db_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    category TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            existing_count = connection.execute(
                "SELECT COUNT(*) AS count FROM products"
            ).fetchone()["count"]
            if existing_count == 0:
                now = int(time.time() * 1000)
                seed_rows = [
                    ("Laptop Pro 14", 1899.99, "computers", now),
                    ("Wireless Mouse", 39.99, "accessories", now),
                    ("Mechanical Keyboard", 129.99, "accessories", now),
                    ("4K Monitor", 499.99, "displays", now),
                ]
                connection.executemany(
                    """
                    INSERT INTO products (name, price, category, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    seed_rows,
                )
            connection.commit()


def cache_get(key: str) -> Any | None:
    try:
        return memcache_client.get(key)
    except (MemcacheError, OSError) as exc:
        app.logger.warning("Memcached get failed for key %s: %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        memcache_client.set(key, value, expire=ttl)
    except (MemcacheError, OSError) as exc:
        app.logger.warning("Memcached set failed for key %s: %s", key, exc)


def memcached_reachable() -> bool:
    probe_key = "healthcheck:probe"
    probe_value = str(int(time.time() * 1000))
    try:
        memcache_client.set(probe_key, probe_value, expire=5)
        return memcache_client.get(probe_key) == probe_value
    except (MemcacheError, OSError) as exc:
        app.logger.warning("Memcached health probe failed: %s", exc)
        return False


def get_products_cache_version() -> str:
    global _products_cache_version
    cached_version = cache_get(PRODUCTS_VERSION_CACHE_KEY)
    if isinstance(cached_version, str):
        _products_cache_version = cached_version
        return cached_version

    cache_set(PRODUCTS_VERSION_CACHE_KEY, _products_cache_version, 86400)
    return _products_cache_version


def bump_products_cache_version() -> None:
    global _products_cache_version
    with version_lock:
        _products_cache_version = str(int(time.time() * 1000))
        cache_set(PRODUCTS_VERSION_CACHE_KEY, _products_cache_version, 86400)


def build_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{prefix}:{digest}"


def cache_api_response(ttl: int) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            cache_key = build_cache_key(
                "api_response",
                {
                    "path": request.path,
                    "query": request.args.to_dict(flat=False),
                    "products_version": get_products_cache_version(),
                },
            )
            cached = cache_get(cache_key)
            if cached is not None:
                response = jsonify(cached["payload"])
                response.status_code = cached["status"]
                response.headers["X-Cache"] = "HIT"
                return response

            result = view_func(*args, **kwargs)
            if isinstance(result, tuple):
                payload, status_code = result
            else:
                payload, status_code = result, 200

            cache_set(cache_key, {"payload": payload, "status": status_code}, ttl)
            response = jsonify(payload)
            response.status_code = status_code
            response.headers["X-Cache"] = "MISS"
            return response

        return wrapper

    return decorator


def query_products(
    min_price: float | None = None, category: str | None = None
) -> list[dict[str, Any]]:
    cache_key = build_cache_key(
        "db_query_products",
        {
            "min_price": min_price,
            "category": category,
            "version": get_products_cache_version(),
        },
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    sql = "SELECT id, name, price, category, updated_at FROM products WHERE 1=1"
    params: list[Any] = []
    if min_price is not None:
        sql += " AND price >= ?"
        params.append(min_price)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id"

    with get_db_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
        result = [dict(row) for row in rows]

    cache_set(cache_key, result, DB_QUERY_TTL)
    return result


def query_product_by_id(product_id: int) -> dict[str, Any] | None:
    cache_key = build_cache_key(
        "db_query_product",
        {"product_id": product_id, "version": get_products_cache_version()},
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return cached["value"]

    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, price, category, updated_at
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

    result = dict(row) if row is not None else None
    cache_set(cache_key, {"value": result}, DB_QUERY_TTL)
    return result


@app.get("/health")
def health() -> tuple[dict[str, Any], int]:
    return {
        "status": "ok",
        "database": DATABASE_PATH,
        "memcached": {
            "host": MEMCACHED_HOST,
            "port": MEMCACHED_PORT,
            "reachable": memcached_reachable(),
        },
        "cache_ttls": {
            "db_query_ttl_seconds": DB_QUERY_TTL,
            "api_response_ttl_seconds": API_RESPONSE_TTL,
        },
    }, 200


@app.get("/products")
@cache_api_response(API_RESPONSE_TTL)
def get_products() -> dict[str, Any]:
    min_price_param = request.args.get("min_price")
    category = request.args.get("category")
    min_price = float(min_price_param) if min_price_param is not None else None
    products = query_products(min_price=min_price, category=category)
    return {
        "products": products,
        "count": len(products),
        "filters": {"min_price": min_price, "category": category},
    }


@app.get("/products/<int:product_id>")
@cache_api_response(API_RESPONSE_TTL)
def get_product(product_id: int) -> tuple[dict[str, Any], int]:
    product = query_product_by_id(product_id)
    if product is None:
        return {"error": "Product not found"}, 404
    return product, 200


@app.post("/products")
def create_product() -> tuple[dict[str, Any], int]:
    payload = request.get_json(force=True, silent=False)
    if not isinstance(payload, dict):
        return {"error": "JSON object body required"}, 400

    required_fields = {"name", "price", "category"}
    missing_fields = sorted(required_fields.difference(payload))
    if missing_fields:
        return {"error": f"Missing required fields: {', '.join(missing_fields)}"}, 400

    now = int(time.time() * 1000)
    with db_lock:
        with get_db_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO products (name, price, category, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(payload["name"]),
                    float(payload["price"]),
                    str(payload["category"]),
                    now,
                ),
            )
            connection.commit()
            product_id = int(cursor.lastrowid)

    bump_products_cache_version()
    product = query_product_by_id(product_id)
    return {"created": product}, 201


@app.get("/reports/expensive-summary")
@cache_api_response(API_RESPONSE_TTL)
def expensive_summary() -> dict[str, Any]:
    products = query_products()
    category_breakdown: dict[str, int] = {}
    total_value = 0.0

    for product in products:
        category = str(product["category"])
        category_breakdown[category] = category_breakdown.get(category, 0) + 1
        total_value += float(product["price"])

    return {
        "generated_at": int(time.time()),
        "product_count": len(products),
        "category_breakdown": category_breakdown,
        "total_inventory_value": round(total_value, 2),
    }


@app.errorhandler(ValueError)
def handle_value_error(error: ValueError) -> tuple[dict[str, str], int]:
    return {"error": str(error)}, 400


@app.errorhandler(BadRequest)
def handle_bad_request(error: BadRequest) -> tuple[dict[str, str], int]:
    return {"error": "Invalid request payload"}, 400


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))