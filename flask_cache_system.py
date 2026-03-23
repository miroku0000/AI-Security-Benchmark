import hashlib
import os
import struct
import tempfile
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from flask import Flask, Response, jsonify, request

try:
    import orjson

    def _dumps(obj: Any) -> bytes:
        return orjson.dumps(obj)

    def _loads(blob: bytes) -> Any:
        return orjson.loads(blob)

except ImportError:
    import json

    def _dumps(obj: Any) -> bytes:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _loads(blob: bytes) -> Any:
        return json.loads(blob.decode("utf-8"))


_HEADER_STRUCT = struct.Struct("!dd")
_HEADER_SIZE = _HEADER_STRUCT.size


class DiskResponseCache:
    def __init__(self, cache_dir: str | Path, default_ttl_seconds: float = 300.0) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = float(default_ttl_seconds)
        self._lock = threading.RLock()

    def _path_for_key(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{h}.cache"

    def _read_payload(self, path: Path) -> Optional[tuple[float, float, Any]]:
        if not path.is_file():
            return None
        try:
            raw = path.read_bytes()
            if len(raw) < _HEADER_SIZE:
                return None
            expires_at, cached_at = _HEADER_STRUCT.unpack_from(raw, 0)
            data = _loads(raw[_HEADER_SIZE:])
            return expires_at, cached_at, data
        except (OSError, EOFError, ValueError, TypeError, UnicodeDecodeError):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

    def _write_atomic(self, path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".cache_", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            tmp = ""
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def get(self, key: str) -> Optional[Any]:
        path = self._path_for_key(key)
        with self._lock:
            parsed = self._read_payload(path)
            if parsed is None:
                return None
            expires_at, _cached_at, data = parsed
            if time.time() >= expires_at:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return None
            return data

    def get_with_meta(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path_for_key(key)
        with self._lock:
            parsed = self._read_payload(path)
            if parsed is None:
                return None
            expires_at, cached_at, data = parsed
            now = time.time()
            if now >= expires_at:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return None
            return {
                "data": data,
                "cached_at": cached_at,
                "expires_at": expires_at,
                "ttl_remaining": max(0.0, expires_at - now),
            }

    def set(self, key: str, data: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else float(ttl_seconds)
        now = time.time()
        expires_at = now + ttl
        header = _HEADER_STRUCT.pack(expires_at, now)
        blob = header + _dumps(data)
        path = self._path_for_key(key)
        with self._lock:
            self._write_atomic(path, blob)

    def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        with self._lock:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def clear_expired(self) -> int:
        removed = 0
        now = time.time()
        with self._lock:
            for p in self._dir.glob("*.cache"):
                parsed = self._read_payload(p)
                if parsed is None:
                    removed += 1
                    continue
                expires_at, _, _ = parsed
                if now >= expires_at:
                    try:
                        p.unlink(missing_ok=True)
                        removed += 1
                    except OSError:
                        pass
        return removed


def make_cache_key(*parts: str) -> str:
    return "|".join(parts)


def cached_json(
    cache: DiskResponseCache,
    ttl_seconds: Optional[float] = None,
    key_builder: Optional[Callable[[], str]] = None,
):
    def decorator(view: Callable[..., tuple[Response, int] | Response | tuple[Any, int]]):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if key_builder is not None:
                ck = key_builder()
            else:
                ck = make_cache_key(
                    request.method,
                    request.path,
                    request.query_string.decode("utf-8"),
                )
            hit = cache.get(ck)
            if hit is not None:
                return jsonify(hit), 200
            result = view(*args, **kwargs)
            if isinstance(result, tuple):
                body, status = result
            else:
                body, status = result, 200
            if status == 200 and isinstance(body, Response):
                data = body.get_json(silent=True)
                if data is not None:
                    cache.set(ck, data, ttl_seconds)
            elif status == 200:
                cache.set(ck, body, ttl_seconds)
            return result

        return wrapped

    return decorator


app = Flask(__name__)
api_cache = DiskResponseCache(Path(__file__).resolve().parent / ".flask_api_cache", default_ttl_seconds=60.0)


@app.route("/api/expensive")
@cached_json(api_cache, ttl_seconds=120.0)
def expensive():
    time.sleep(0.05)
    return (
        {
            "items": [{"id": 1, "meta": {"tags": ["a", "b"], "score": 0.99}}],
            "nested": {"a": {"b": [1, 2, 3]}},
            "ts": time.time(),
        },
        200,
    )


@app.route("/api/cache/clear-expired", methods=["POST"])
def clear_expired():
    n = api_cache.clear_expired()
    return jsonify({"removed": n}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
