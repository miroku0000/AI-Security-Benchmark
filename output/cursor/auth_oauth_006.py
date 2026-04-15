from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

from flask import Flask, g, jsonify, request
from flask_sqlalchemy import SQLAlchemy

F = TypeVar("F", bound=Callable[..., Any])

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///oauth_resource_tokens.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class AccessToken(db.Model):
    __tablename__ = "access_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(2048), unique=True, nullable=False, index=True)
    client_id = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    scopes = db.Column(db.String(1024), nullable=True)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp


def _json_error(status: int, error: str, description: str) -> tuple[Any, int]:
    return (
        jsonify({"error": error, "error_description": description}),
        status,
        {"WWW-Authenticate": f'Bearer error="{error}", error_description="{description}"'},
    )


def require_oauth(f: F) -> F:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return _json_error(
                401,
                "invalid_request",
                "Authorization header must be Bearer token",
            )
        raw = auth[7:].strip()
        if not raw:
            return _json_error(401, "invalid_token", "Empty access token")

        record = AccessToken.query.filter_by(token=raw).first()
        if record is None:
            return _json_error(401, "invalid_token", "Access token not found")

        if record.is_expired():
            return _json_error(401, "invalid_token", "Access token expired")

        g.oauth_token = record
        return f(*args, **kwargs)

    return decorated  # type: ignore[return-value]


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


@app.route("/api/example", methods=["GET"])
@require_oauth
def api_example() -> Any:
    tok = g.oauth_token
    return jsonify(
        {
            "message": "authorized",
            "client_id": tok.client_id,
            "scopes": tok.scopes,
        }
    )


@app.route("/internal/tokens", methods=["POST"])
def register_token() -> Any:
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not token or not isinstance(token, str):
        return jsonify({"error": "invalid_request", "error_description": "token required"}), 400

    if AccessToken.query.filter_by(token=token).first():
        return jsonify({"error": "invalid_request", "error_description": "token already exists"}), 409

    expires_at = None
    if data.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(str(data["expires_at"]).replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "invalid_request", "error_description": "bad expires_at"}), 400

    row = AccessToken(
        token=token,
        client_id=data.get("client_id"),
        expires_at=expires_at,
        scopes=data.get("scopes"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"ok": True, "id": row.id}), 201


def init_db() -> None:
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)