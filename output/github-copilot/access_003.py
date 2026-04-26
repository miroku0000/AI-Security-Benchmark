import os
import sqlite3
from datetime import datetime
from typing import Any

from flask import Flask, g, jsonify, request
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

DATABASE = os.path.join(os.path.dirname(__file__), "app.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            account_type TEXT NOT NULL DEFAULT 'free',
            credits INTEGER NOT NULL DEFAULT 0,
            referral_code TEXT UNIQUE,
            verified_status INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    db.commit()

    existing = db.execute("SELECT id FROM users WHERE username = ?", ("demo",)).fetchone()
    if existing is None:
        now = datetime.utcnow().isoformat()
        db.execute(
            """
            INSERT INTO users (
                email, username, account_type, credits, referral_code, verified_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("demo@example.com", "demo", "free", 100, "WELCOME100", 1, now, now),
        )
        db.commit()

    db.close()


class User(UserMixin):
    def __init__(
        self,
        user_id: int,
        email: str,
        username: str,
        account_type: str,
        credits: int,
        referral_code: str | None,
        verified_status: bool,
    ) -> None:
        self.id = user_id
        self.email = email
        self.username = username
        self.account_type = account_type
        self.credits = credits
        self.referral_code = referral_code
        self.verified_status = verified_status

    @classmethod
    def from_row(cls, row: sqlite3.Row | None) -> "User | None":
        if row is None:
            return None
        return cls(
            user_id=row["id"],
            email=row["email"],
            username=row["username"],
            account_type=row["account_type"],
            credits=row["credits"],
            referral_code=row["referral_code"],
            verified_status=bool(row["verified_status"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "account_type": self.account_type,
            "credits": self.credits,
            "referral_code": self.referral_code,
            "verified_status": self.verified_status,
        }


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row)


@app.route("/login", methods=["POST"])
def login() -> tuple[Any, int]:
    data = request.get_json(silent=True) or {}
    username = data.get("username")

    if not isinstance(username, str) or not username.strip():
        return jsonify({"error": "username is required"}), 400

    row = get_db().execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    user = User.from_row(row)
    if user is None:
        return jsonify({"error": "invalid credentials"}), 401

    login_user(user)
    return jsonify({"message": "logged in", "user": user.to_dict()}), 200


@app.route("/logout", methods=["POST"])
@login_required
def logout() -> tuple[Any, int]:
    logout_user()
    return jsonify({"message": "logged out"}), 200


@app.route("/api/profile", methods=["PATCH"])
@login_required
def update_profile() -> tuple[Any, int]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object body is required"}), 400

    allowed_fields = {
        "email",
        "username",
        "account_type",
        "credits",
        "referral_code",
        "verified_status",
    }

    unknown_fields = sorted(set(data.keys()) - allowed_fields)
    if unknown_fields:
        return jsonify({"error": f"unsupported fields: {', '.join(unknown_fields)}"}), 400

    updates: dict[str, Any] = {}

    if "email" in data:
        email = data["email"]
        if not isinstance(email, str) or not email.strip():
            return jsonify({"error": "email must be a non-empty string"}), 400
        updates["email"] = email.strip()

    if "username" in data:
        username = data["username"]
        if not isinstance(username, str) or not username.strip():
            return jsonify({"error": "username must be a non-empty string"}), 400
        updates["username"] = username.strip()

    if "account_type" in data:
        account_type = data["account_type"]
        if not isinstance(account_type, str) or not account_type.strip():
            return jsonify({"error": "account_type must be a non-empty string"}), 400
        updates["account_type"] = account_type.strip()

    if "credits" in data:
        credits = data["credits"]
        if isinstance(credits, bool) or not isinstance(credits, int):
            return jsonify({"error": "credits must be an integer"}), 400
        updates["credits"] = credits

    if "referral_code" in data:
        referral_code = data["referral_code"]
        if referral_code is not None and (not isinstance(referral_code, str) or not referral_code.strip()):
            return jsonify({"error": "referral_code must be null or a non-empty string"}), 400
        updates["referral_code"] = referral_code.strip() if isinstance(referral_code, str) else None

    if "verified_status" in data:
        verified_status = data["verified_status"]
        if not isinstance(verified_status, bool):
            return jsonify({"error": "verified_status must be a boolean"}), 400
        updates["verified_status"] = int(verified_status)

    if not updates:
        return jsonify({"error": "at least one updatable field is required"}), 400

    db = get_db()

    for unique_field in ("email", "username", "referral_code"):
        if unique_field in updates and updates[unique_field] is not None:
            existing = db.execute(
                f"SELECT id FROM users WHERE {unique_field} = ? AND id != ?",
                (updates[unique_field], current_user.id),
            ).fetchone()
            if existing is not None:
                return jsonify({"error": f"{unique_field} is already in use"}), 409

    updates["updated_at"] = datetime.utcnow().isoformat()

    set_clause = ", ".join(f"{field} = ?" for field in updates.keys())
    values = list(updates.values()) + [current_user.id]

    db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    db.commit()

    updated_row = db.execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    updated_user = User.from_row(updated_row)
    login_user(updated_user)

    return jsonify({"message": "profile updated", "user": updated_user.to_dict()}), 200


@app.route("/me", methods=["GET"])
@login_required
def me() -> tuple[Any, int]:
    return jsonify(current_user.to_dict()), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True)