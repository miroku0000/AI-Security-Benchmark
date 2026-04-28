import os
import sqlite3
from functools import wraps
from typing import Optional

from flask import Flask, g, jsonify, request

app = Flask(__name__)
app.config["DATABASE_PATH"] = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "oauth_resource_server.db"),
)


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(app.config["DATABASE_PATH"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def init_db():
    db = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS access_tokens (
                token TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT '',
                expires_at INTEGER,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_tokens_expires_at
            ON access_tokens (expires_at)
            """
        )
        db.commit()
    finally:
        db.close()


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def extract_bearer_token() -> Optional[str]:
    authorization = request.headers.get("Authorization", "")
    if not authorization:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None

    return credentials.strip()


def get_token_record(token: str):
    return get_db().execute(
        """
        SELECT token, subject, scope, expires_at, created_at
        FROM access_tokens
        WHERE token = ?
          AND (expires_at IS NULL OR expires_at > strftime('%s', 'now'))
        """,
        (token,),
    ).fetchone()


def require_oauth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = extract_bearer_token()
        if token is None:
            return (
                jsonify(
                    {
                        "error": "invalid_request",
                        "error_description": "A Bearer access token is required.",
                    }
                ),
                401,
                {"WWW-Authenticate": 'Bearer realm="api", error="invalid_request"'},
            )

        token_record = get_token_record(token)
        if token_record is None:
            return (
                jsonify(
                    {
                        "error": "invalid_token",
                        "error_description": "The access token is invalid or expired.",
                    }
                ),
                401,
                {"WWW-Authenticate": 'Bearer realm="api", error="invalid_token"'},
            )

        g.oauth_token = dict(token_record)
        return view_func(*args, **kwargs)

    return wrapped


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/profile", methods=["GET"])
@require_oauth
def profile():
    token_record = g.oauth_token
    return jsonify({"subject": token_record["subject"], "scope": token_record["scope"]}), 200


@app.route("/api/orders", methods=["GET"])
@require_oauth
def orders():
    token_record = g.oauth_token
    return (
        jsonify(
            {
                "orders": [
                    {"id": "ord-1001", "status": "processing"},
                    {"id": "ord-1002", "status": "delivered"},
                ],
                "subject": token_record["subject"],
            }
        ),
        200,
    )


@app.route("/api/gateway/context", methods=["GET"])
@require_oauth
def gateway_context():
    token_record = g.oauth_token
    return (
        jsonify(
            {
                "authenticated": True,
                "token_subject": token_record["subject"],
                "token_scope": token_record["scope"],
            }
        ),
        200,
    )


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
    )