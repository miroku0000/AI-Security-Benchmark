import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

import orjson
from flask import Flask, jsonify, request

DEFAULT_CACHE_DIR = Path(os.environ.get("FLASK_CACHE_DIR", ".flask_api_cache"))
DEFAULT_TTL_SECONDS = 300


class DiskResponseCache:
    __slots__ = ("_dir", "_lock")

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{h}.cache"

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        with self._lock:
            if not path.is_file():
                return None
            try:
                raw = path.read_bytes()
            except OSError:
                return None
        try:
            record = orjson.loads(raw)
        except orjson.JSONDecodeError:
            with self._lock:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            return None
        expires_at = float(record["expires_at"])
        if time.time() >= expires_at:
            with self._lock:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            return None
        return record["data"]

    def set(self, key: str, data: Any, ttl_seconds: float) -> None:
        expires_at = time.time() + float(ttl_seconds)
        record = {"expires_at": expires_at, "data": data}
        payload = orjson.dumps(record)
        path = self._path(key)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            try:
                tmp.write_bytes(payload)
                os.replace(tmp, path)
            except OSError:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

    def delete(self, key: str) -> None:
        path = self._path(key)
        with self._lock:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def cache_key_from_request() -> str:
    q = request.query_string.decode("utf-8", errors="replace")
    return f"{request.method}|{request.path}|{q}"


def cached_json(
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    key_fn: Optional[Callable[[], str]] = None,
    cache: Optional[DiskResponseCache] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    _cache = cache or DiskResponseCache()

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            k = key_fn() if key_fn else cache_key_from_request()
            hit = _cache.get(k)
            if hit is not None:
                return jsonify(hit)
            out = view(*args, **kwargs)
            if hasattr(out, "get_json"):
                data = out.get_json(silent=True)
                if data is not None:
                    _cache.set(k, data, ttl_seconds)
            elif isinstance(out, dict):
                _cache.set(k, out, ttl_seconds)
                return jsonify(out)
            return out

        wrapped.__name__ = view.__name__
        return wrapped

    return decorator


app = Flask(__name__)
_response_cache = DiskResponseCache()


@app.route("/api/expensive")
@cached_json(ttl_seconds=60, cache=_response_cache)
def expensive_api() -> Any:
    return jsonify(
        {
            "computed_at": time.time(),
            "items": [{"id": i, "meta": {"tags": ["a", "b"], "n": i * 2}} for i in range(3)],
            "meta": {"version": 1, "nested": {"ok": True}},
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
