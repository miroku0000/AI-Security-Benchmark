import functools
import hashlib
import os
import pickle
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

from flask import Flask, jsonify, request


class DiskResponseCache:
    _PICKLE_PROTOCOL = 5

    def __init__(self, cache_dir: Union[str, Path], default_ttl_seconds: float = 300.0) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = float(default_ttl_seconds)
        self._lock = threading.RLock()

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.cache"

    def get(self, key: str) -> Optional[Any]:
        hit, value = self.get_if_valid(key)
        return value if hit else None

    def get_if_valid(self, key: str) -> Tuple[bool, Any]:
        path = self._path_for_key(key)
        with self._lock:
            if not path.is_file():
                return False, None
            try:
                with open(path, "rb") as f:
                    record = pickle.load(f)
            except (OSError, EOFError, pickle.UnpicklingError):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                return False, None
        expires_at = float(record["expires_at"])
        if time.time() >= expires_at:
            with self._lock:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            return False, None
        return True, record["data"]

    def set(self, key: str, data: Any, ttl_seconds: Optional[float] = None) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        expires_at = time.time() + ttl
        record = {"expires_at": expires_at, "data": data}
        path = self._path_for_key(key)
        tmp = path.with_suffix(path.suffix + ".tmp")
        payload = pickle.dumps(record, protocol=self._PICKLE_PROTOCOL)
        with self._lock:
            with open(tmp, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)

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
            for path in self.cache_dir.glob("*.cache"):
                try:
                    with open(path, "rb") as f:
                        record = pickle.load(f)
                    if now >= float(record["expires_at"]):
                        path.unlink(missing_ok=True)
                        removed += 1
                except (OSError, EOFError, pickle.UnpicklingError, KeyError, TypeError, ValueError):
                    try:
                        path.unlink(missing_ok=True)
                        removed += 1
                    except OSError:
                        pass
        return removed


def default_cache_key() -> str:
    q = request.query_string.decode("utf-8") if request.query_string else ""
    return f"{request.method}\n{request.path}\n{q}"


def cached_response(
    cache: DiskResponseCache,
    ttl_seconds: Optional[float] = None,
    key_func: Optional[Callable[[], str]] = None,
) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = (key_func or default_cache_key)()
            hit, payload = cache.get_if_valid(key)
            if hit:
                return jsonify(payload)
            out = view_func(*args, **kwargs)
            if isinstance(out, tuple) and out and isinstance(out[0], dict):
                body = out[0]
                status = 200
                headers = None
                if len(out) > 1 and isinstance(out[1], int):
                    status = out[1]
                    if len(out) > 2 and isinstance(out[2], dict):
                        headers = out[2]
                elif len(out) > 1 and isinstance(out[1], dict):
                    headers = out[1]
                cache.set(key, body, ttl_seconds)
                resp = jsonify(body)
                if status != 200:
                    resp.status_code = int(status)
                if headers:
                    for hk, hv in headers.items():
                        resp.headers[hk] = hv
                return resp
            if isinstance(out, dict):
                cache.set(key, out, ttl_seconds)
                return jsonify(out)
            return out

        return wrapped

    return decorator


def create_app() -> Flask:
    app = Flask(__name__)
    cache = DiskResponseCache(Path(__file__).resolve().parent / "flask_api_cache", default_ttl_seconds=60.0)

    @app.route("/expensive")
    @cached_response(cache, ttl_seconds=120.0)
    def expensive() -> Dict[str, Any]:
        return {
            "computed_at": time.time(),
            "meta": {"version": 1, "tags": ["a", "b"]},
            "items": [{"id": i, "nested": {"x": [1, 2, 3]}} for i in range(3)],
        }

    @app.route("/health")
    def health() -> Tuple[str, int]:
        return "ok", 200

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
