import functools
import json
import os
import secrets
import time
import uuid
from typing import Any, Callable, ParamSpec, TypeVar

import redis
from flask import Flask, Request, Response, g, request

P = ParamSpec("P")
R = TypeVar("R")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SESSION_COOKIE = "sid"
SESSION_PREFIX = "session:"
SESSION_TTL = int(os.environ.get("SESSION_TTL", 86400))
CACHE_PREFIX = "cache:"
DEFAULT_CACHE_TTL = int(os.environ.get("CACHE_TTL", 300))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")


def _session_key(sid: str) -> str:
    return f"{SESSION_PREFIX}{sid}"


def _load_session(sid: str) -> dict[str, Any]:
    raw = r.get(_session_key(sid))
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_session(sid: str, data: dict[str, Any]) -> None:
    r.set(_session_key(sid), json.dumps(data), ex=SESSION_TTL)


def get_session_id(req: Request) -> str:
    sid = req.cookies.get(SESSION_COOKIE)
    if sid and r.exists(_session_key(sid)):
        return sid
    return secrets.token_urlsafe(32)


@app.before_request
def before_request() -> None:
    sid = get_session_id(request)
    g.session_id = sid
    g.session = _load_session(sid)


@app.after_request
def after_request(response: Response) -> Response:
    sid = getattr(g, "session_id", None)
    sess = getattr(g, "session", None)
    if sid is not None and isinstance(sess, dict):
        _save_session(sid, sess)
        response.set_cookie(
            SESSION_COOKIE,
            sid,
            max_age=SESSION_TTL,
            httponly=True,
            samesite="Lax",
        )
    return response


def cache_redis(
    ttl: int = DEFAULT_CACHE_TTL,
    key_prefix: str = "",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            base = key_prefix or func.__name__
            payload = {"a": args, "k": kwargs}
            cache_key = f"{CACHE_PREFIX}{base}:{json.dumps(payload, sort_keys=True, default=str)}"
            cached = r.get(cache_key)
            if cached is not None:
                return json.loads(cached)
            result = func(*args, **kwargs)
            r.set(cache_key, json.dumps(result, default=str), ex=ttl)
            return result

        return wrapper

    return decorator


def mock_db_expensive_query(user_id: str) -> dict[str, Any]:
    time.sleep(0.05)
    return {"user_id": user_id, "balance": 100, "tier": "gold"}


@cache_redis(ttl=60, key_prefix="user_profile")
def get_user_profile(user_id: str) -> dict[str, Any]:
    return mock_db_expensive_query(user_id)


@app.route("/")
def index() -> str:
    visits = int(g.session.get("visits", 0)) + 1
    g.session["visits"] = visits
    g.session["last_path"] = "/"
    return f"visits={visits} session_id={g.session_id[:8]}..."


@app.route("/login")
def login() -> str:
    g.session["user_id"] = str(uuid.uuid4())
    g.session["authenticated"] = True
    return "logged_in"


@app.route("/profile/<user_id>")
def profile(user_id: str) -> tuple[str, int]:
    data = get_user_profile(user_id)
    return json.dumps(data), 200, {"Content-Type": "application/json"}


@app.route("/health")
def health() -> tuple[str, int]:
    try:
        r.ping()
        return "ok", 200
    except redis.RedisError:
        return "redis_unavailable", 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))