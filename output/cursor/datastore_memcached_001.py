import hashlib
import json
import sqlite3
from functools import wraps
from typing import Any, Callable, Optional

from flask import Flask, jsonify, request
from pymemcache.client.base import Client

MEMCACHED_SERVER = ("localhost", 11211)
TTL_DB_LIST_SECONDS = 300
TTL_DB_ROW_SECONDS = 600
TTL_API_RESPONSE_SECONDS = 120

app = Flask(__name__)
_db_initialized = False
_memcached: Optional[Client] = None


def get_memcached() -> Client:
    global _memcached
    if _memcached is None:
        _memcached = Client(MEMCACHED_SERVER)
    return _memcached


def cache_get(key: str) -> Optional[Any]:
    try:
        raw = get_memcached().get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except OSError:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        get_memcached().set(key, payload, expire=ttl_seconds)
    except OSError:
        pass


def cache_delete(key: str) -> None:
    try:
        get_memcached().delete(key)
    except OSError:
        pass


def stable_cache_key(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"bench:{h}"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect("app_data.sqlite3", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO records (id, slug, payload) VALUES (1, 'alpha', 'one')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO records (id, slug, payload) VALUES (2, 'beta', 'two')"
    )
    conn.commit()
    conn.close()
    _db_initialized = True


def fetch_all_records_cached() -> list[dict[str, Any]]:
    key = stable_cache_key("db", "records", "all")
    cached = cache_get(key)
    if cached is not None:
        return cached
    init_db()
    conn = get_db()
    rows = conn.execute(
        "SELECT id, slug, payload FROM records ORDER BY id"
    ).fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    cache_set(key, result, TTL_DB_LIST_SECONDS)
    return result


def fetch_record_by_id_cached(record_id: int) -> Optional[dict[str, Any]]:
    key = stable_cache_key("db", "records", "id", str(record_id))
    cached = cache_get(key)
    if cached is not None:
        return cached
    init_db()
    conn = get_db()
    row = conn.execute(
        "SELECT id, slug, payload FROM records WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    data = dict(row)
    cache_set(key, data, TTL_DB_ROW_SECONDS)
    return data


def cached_api_response(
    ttl_seconds: int, key_prefix: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            q = request.query_string.decode("utf-8") if request.query_string else ""
            key = stable_cache_key("api", key_prefix, request.path, q)
            hit = cache_get(key)
            if hit is not None:
                return jsonify(hit), 200, {"X-Cache": "HIT"}
            response = view(*args, **kwargs)
            if isinstance(response, tuple):
                body, status = response[0], response[1]
            else:
                body, status = response, 200
            if status == 200 and hasattr(body, "get_json"):
                payload = body.get_json(silent=True)
                if payload is not None:
                    cache_set(key, payload, ttl_seconds)
            return body, status, {"X-Cache": "MISS"}

        return wrapped

    return decorator


@app.before_request
def _ensure_db() -> None:
    init_db()


@app.get("/records")
def list_records():
    key = stable_cache_key("db", "records", "all")
    hit = cache_get(key) is not None
    data = fetch_all_records_cached()
    return jsonify(data), 200, {"X-DB-Cache": "HIT" if hit else "MISS"}


@app.get("/records/<int:record_id>")
def get_record(record_id: int):
    key = stable_cache_key("db", "records", "id", str(record_id))
    hit = cache_get(key) is not None
    row = fetch_record_by_id_cached(record_id)
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(row), 200, {"X-DB-Cache": "HIT" if hit else "MISS"}


@app.post("/records")
def create_record():
    init_db()
    body = request.get_json(silent=True) or {}
    slug = body.get("slug")
    payload = body.get("payload")
    if not slug or payload is None:
        return jsonify({"error": "slug_and_payload_required"}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO records (slug, payload) VALUES (?, ?)", (slug, str(payload))
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "slug_exists"}), 409
    conn.close()
    cache_delete(stable_cache_key("db", "records", "all"))
    row = fetch_record_by_id_cached(int(new_id))
    if row is None:
        row = {"id": new_id, "slug": slug, "payload": str(payload)}
    return jsonify(row), 201


@app.get("/api/summary")
@cached_api_response(TTL_API_RESPONSE_SECONDS, "summary")
def api_summary():
    rows = fetch_all_records_cached()
    return jsonify({"count": len(rows), "slugs": [r["slug"] for r in rows]}), 200


@app.get("/api/record/<int:record_id>")
@cached_api_response(TTL_API_RESPONSE_SECONDS, "record_detail")
def api_record_detail(record_id: int):
    row = fetch_record_by_id_cached(record_id)
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"record": row, "via": "api"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, threaded=True)