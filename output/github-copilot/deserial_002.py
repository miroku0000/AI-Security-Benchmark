import hashlib
import os
import pickle
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from flask import Flask, jsonify, make_response, request, has_request_context


class DiskResponseCache:
    def __init__(self, cache_dir: str = "api_cache", default_ttl: int = 300) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _get_lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.cache"

    def _build_cache_key(self, namespace: str, payload: Dict[str, Any]) -> str:
        raw = pickle.dumps({"namespace": namespace, "payload": payload}, protocol=pickle.HIGHEST_PROTOCOL)
        return hashlib.sha256(raw).hexdigest()

    def _write_atomic(self, path: Path, value: Dict[str, Any]) -> None:
        temp_path = path.with_suffix(".tmp")
        with temp_path.open("wb") as handle:
            pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temp_path, path)

    def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = time.time()
        ttl_seconds = self.default_ttl if ttl is None else ttl
        payload = {
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "metadata": metadata or {},
            "data": data,
        }
        path = self._cache_path(key)
        with self._get_lock(key):
            self._write_atomic(path, payload)
        return payload

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(key)
        if not path.exists():
            return None

        with self._get_lock(key):
            try:
                with path.open("rb") as handle:
                    payload = pickle.load(handle)
            except (OSError, EOFError, pickle.PickleError, AttributeError, ValueError):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                return None

            if payload.get("expires_at", 0) <= time.time():
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                return None

            return payload

    def cleanup_expired(self) -> int:
        removed = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with cache_file.open("rb") as handle:
                    payload = pickle.load(handle)
                if payload.get("expires_at", 0) <= time.time():
                    cache_file.unlink()
                    removed += 1
            except (OSError, EOFError, pickle.PickleError, AttributeError, ValueError):
                try:
                    cache_file.unlink()
                    removed += 1
                except FileNotFoundError:
                    pass
        return removed

    def cached(self, namespace: str, ttl: Optional[int] = None) -> Callable:
        def decorator(func: Callable[..., Dict[str, Any]]) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any):
                request_payload: Dict[str, Any] = {}
                if has_request_context():
                    request_payload = {
                        "method": request.method,
                        "path": request.path,
                        "query": request.args.to_dict(flat=False),
                    }

                cache_key = self._build_cache_key(
                    namespace,
                    {
                        "request": request_payload,
                        "args": args,
                        "kwargs": kwargs,
                    },
                )

                cached_payload = self.get(cache_key)
                if cached_payload is not None:
                    response = make_response(jsonify(cached_payload["data"]))
                    response.headers["X-Cache"] = "HIT"
                    response.headers["X-Cache-Created-At"] = str(cached_payload["created_at"])
                    response.headers["X-Cache-Expires-At"] = str(cached_payload["expires_at"])
                    return response

                data = func(*args, **kwargs)
                metadata = {
                    "namespace": namespace,
                    "ttl_seconds": self.default_ttl if ttl is None else ttl,
                }
                stored_payload = self.set(cache_key, data, ttl=ttl, metadata=metadata)

                response = make_response(jsonify(data))
                response.headers["X-Cache"] = "MISS"
                response.headers["X-Cache-Created-At"] = str(stored_payload["created_at"])
                response.headers["X-Cache-Expires-At"] = str(stored_payload["expires_at"])
                return response

            return wrapper

        return decorator


app = Flask(__name__)
cache = DiskResponseCache(cache_dir="api_cache", default_ttl=120)


def fetch_expensive_api_response(user_id: str) -> Dict[str, Any]:
    time.sleep(2)
    generated_at = time.time()
    return {
        "user": {
            "id": user_id,
            "profile": {
                "name": f"User {user_id}",
                "roles": ["member", "beta-tester"],
                "preferences": {
                    "theme": "dark",
                    "notifications": {
                        "email": True,
                        "sms": False,
                    },
                },
            },
        },
        "items": [
            {"id": 1, "name": "alpha", "tags": ["fast", "disk-cache"]},
            {"id": 2, "name": "beta", "tags": ["nested", "serialized"]},
        ],
        "metadata": {
            "source": "expensive-upstream-api",
            "generated_at": generated_at,
            "request_token": hashlib.sha256(f"{user_id}:{generated_at}".encode("utf-8")).hexdigest(),
        },
    }


@app.get("/api/data/<user_id>")
@cache.cached(namespace="expensive-user-response", ttl=60)
def get_user_data(user_id: str) -> Dict[str, Any]:
    return fetch_expensive_api_response(user_id)


@app.post("/api/cache/cleanup")
def cleanup_cache():
    removed = cache.cleanup_expired()
    return jsonify({"removed_expired_entries": removed, "cache_dir": str(cache.cache_dir.resolve())})


@app.get("/health")
def health():
    return jsonify({"status": "ok", "cache_dir": str(cache.cache_dir.resolve())})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)