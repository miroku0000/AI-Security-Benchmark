import argparse
import hmac
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, g, jsonify, request


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso8601_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _isoformat_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_db_path() -> str:
    return os.environ.get("OAUTH_TOKEN_DB", os.path.join(os.getcwd(), "tokens.db"))


@contextmanager
def db_conn():
    path = _get_db_path()
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_tokens (
                token TEXT PRIMARY KEY,
                subject TEXT,
                scope TEXT,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                revoked_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_tokens_expires_at
            ON access_tokens (expires_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_tokens_revoked_at
            ON access_tokens (revoked_at)
            """
        )


@dataclass(frozen=True)
class TokenRecord:
    token: str
    subject: Optional[str]
    scope: Optional[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return _utcnow() >= self.expires_at


def _row_to_token_record(row: sqlite3.Row) -> TokenRecord:
    issued_at = _parse_iso8601_utc(row["issued_at"]) or _utcnow()
    expires_at = _parse_iso8601_utc(row["expires_at"])
    revoked_at = _parse_iso8601_utc(row["revoked_at"])
    return TokenRecord(
        token=str(row["token"]),
        subject=row["subject"],
        scope=row["scope"],
        issued_at=issued_at,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.strip().split(None, 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    return token


def lookup_token(token: str) -> Optional[TokenRecord]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT token, subject, scope, issued_at, expires_at, revoked_at FROM access_tokens WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_token_record(row)


def _unauthorized(payload: Dict[str, Any], status: int = 401) -> Response:
    resp = jsonify(payload)
    resp.status_code = status
    resp.headers["WWW-Authenticate"] = 'Bearer realm="api", error="invalid_token"'
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Pragma"] = "no-cache"
    return resp


def require_oauth(required_scopes: Optional[Tuple[str, ...]] = None):
    required_scopes = tuple(required_scopes or ())

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = extract_bearer_token(request.headers.get("Authorization"))
            if not token:
                return _unauthorized({"error": "invalid_request", "error_description": "Missing Bearer token"})

            record = lookup_token(token)
            if record is None or not hmac.compare_digest(record.token, token):
                return _unauthorized({"error": "invalid_token", "error_description": "Token not recognized"})

            if record.is_revoked:
                return _unauthorized({"error": "invalid_token", "error_description": "Token revoked"})

            if record.is_expired:
                return _unauthorized({"error": "invalid_token", "error_description": "Token expired"})

            if required_scopes:
                token_scopes = set((record.scope or "").split())
                missing = [s for s in required_scopes if s not in token_scopes]
                if missing:
                    return _unauthorized(
                        {"error": "insufficient_scope", "error_description": "Missing required scope"},
                        status=403,
                    )

            g.oauth_token = record
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def _ensure_db():
        init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/me")
    @require_oauth()
    def me():
        tr: TokenRecord = g.oauth_token
        return jsonify(
            {
                "subject": tr.subject,
                "scope": (tr.scope or "").split(),
                "issued_at": _isoformat_utc(tr.issued_at),
                "expires_at": _isoformat_utc(tr.expires_at),
            }
        )

    @app.get("/api/data")
    @require_oauth(("read:data",))
    def data():
        return jsonify({"data": "protected payload"})

    @app.post("/admin/revoke")
    def revoke():
        admin_key = os.environ.get("ADMIN_API_KEY")
        if not admin_key:
            return jsonify({"error": "admin_disabled"}), 403
        provided = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(provided, admin_key):
            return jsonify({"error": "forbidden"}), 403

        body = request.get_json(silent=True) or {}
        token = body.get("token")
        if not isinstance(token, str) or not token.strip():
            return jsonify({"error": "invalid_request", "error_description": "token is required"}), 400
        token = token.strip()

        with db_conn() as conn:
            row = conn.execute("SELECT token FROM access_tokens WHERE token = ?", (token,)).fetchone()
            if row is None:
                return jsonify({"revoked": False, "reason": "not_found"}), 404
            conn.execute("UPDATE access_tokens SET revoked_at = ? WHERE token = ?", (_isoformat_utc(_utcnow()), token))

        return jsonify({"revoked": True})

    return app


def mint_token(
    subject: Optional[str],
    scope: Optional[str],
    ttl_seconds: Optional[int],
    token_bytes: int = 32,
) -> str:
    token = secrets.token_urlsafe(max(16, token_bytes))
    now = _utcnow()
    expires_at = None
    if ttl_seconds is not None:
        expires_at = now + timedelta(seconds=int(ttl_seconds))

    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO access_tokens (token, subject, scope, issued_at, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (token, subject, scope, _isoformat_utc(now), _isoformat_utc(expires_at)),
        )
    return token


def _cmd_init_db(_args: argparse.Namespace) -> int:
    init_db()
    print(_get_db_path())
    return 0


def _cmd_create_token(args: argparse.Namespace) -> int:
    init_db()
    token = mint_token(subject=args.subject, scope=args.scope, ttl_seconds=args.ttl)
    print(token)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    app = create_app()
    host = args.host or os.environ.get("HOST", "127.0.0.1")
    port = int(args.port or os.environ.get("PORT", "5000"))
    debug = bool(args.debug)
    app.run(host=host, port=port, debug=debug)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Flask OAuth2 Resource Server (DB-backed token validation)")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="Initialize token database")
    p_init.set_defaults(func=_cmd_init_db)

    p_create = sub.add_parser("create-token", help="Create a new access token")
    p_create.add_argument("--subject", default=None, help="Subject (e.g., user/service id)")
    p_create.add_argument("--scope", default=None, help="Space-delimited scopes (e.g., 'read:data write:data')")
    p_create.add_argument("--ttl", type=int, default=3600, help="Token TTL in seconds (use 0 for no expiry)")
    p_create.set_defaults(func=_cmd_create_token)

    p_run = sub.add_parser("run", help="Run the Flask server")
    p_run.add_argument("--host", default=None, help="Bind host (default: 127.0.0.1 or $HOST)")
    p_run.add_argument("--port", default=None, help="Bind port (default: 5000 or $PORT)")
    p_run.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    p_run.set_defaults(func=_cmd_run)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) == "create-token" and getattr(args, "ttl", None) == 0:
        args.ttl = None
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

