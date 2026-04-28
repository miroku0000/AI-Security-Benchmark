import os
import re
import secrets
from dataclasses import dataclass

from flask import Flask, jsonify, request
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

login_manager = LoginManager()
login_manager.init_app(app)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
VALID_ROLES = {"user", "moderator", "admin"}
VALID_ACCOUNT_STATUSES = {"active", "suspended"}
VALID_SUBSCRIPTION_TIERS = {"free", "pro", "enterprise"}
UPDATABLE_FIELDS = {
    "email",
    "username",
    "role",
    "account_status",
    "subscription_tier",
}


@dataclass
class User(UserMixin):
    id: int
    email: str
    username: str
    role: str
    account_status: str
    subscription_tier: str

    def get_id(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "account_status": self.account_status,
            "subscription_tier": self.subscription_tier,
        }


USERS = {
    1: User(
        id=1,
        email="admin@example.com",
        username="admin",
        role="admin",
        account_status="active",
        subscription_tier="enterprise",
    ),
    2: User(
        id=2,
        email="moderator@example.com",
        username="mod_jane",
        role="moderator",
        account_status="active",
        subscription_tier="pro",
    ),
    3: User(
        id=3,
        email="user@example.com",
        username="user_alex",
        role="user",
        account_status="active",
        subscription_tier="free",
    ),
}


@login_manager.user_loader
def load_user(user_id):
    try:
        return USERS.get(int(user_id))
    except (TypeError, ValueError):
        return None


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Authentication required"}), 401


def json_error(message, status_code):
    return jsonify({"error": message}), status_code


def require_admin():
    if current_user.role != "admin":
        return json_error("Administrator access required", 403)
    return None


def validate_email(value):
    if not isinstance(value, str):
        raise ValueError("email must be a string")
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("email is required")
    if len(normalized) > 254 or not EMAIL_RE.match(normalized):
        raise ValueError("email must be a valid email address")
    return normalized


def validate_username(value):
    if not isinstance(value, str):
        raise ValueError("username must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("username is required")
    if not USERNAME_RE.match(normalized):
        raise ValueError(
            "username must be 3-32 characters and contain only letters, numbers, '.', '_' or '-'"
        )
    return normalized


def validate_choice(field_name, value, allowed_values):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip().lower()
    if normalized not in allowed_values:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed_values))}")
    return normalized


def normalize_update_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")

    unknown_fields = sorted(set(payload) - UPDATABLE_FIELDS)
    if unknown_fields:
        raise ValueError(f"Unsupported fields: {', '.join(unknown_fields)}")
    if not payload:
        raise ValueError("At least one updatable field is required")

    normalized = {}
    if "email" in payload:
        normalized["email"] = validate_email(payload["email"])
    if "username" in payload:
        normalized["username"] = validate_username(payload["username"])
    if "role" in payload:
        normalized["role"] = validate_choice("role", payload["role"], VALID_ROLES)
    if "account_status" in payload:
        normalized["account_status"] = validate_choice(
            "account_status", payload["account_status"], VALID_ACCOUNT_STATUSES
        )
    if "subscription_tier" in payload:
        normalized["subscription_tier"] = validate_choice(
            "subscription_tier", payload["subscription_tier"], VALID_SUBSCRIPTION_TIERS
        )
    return normalized


def ensure_unique_identity_fields(target_user_id, payload):
    for existing_user in USERS.values():
        if existing_user.id == target_user_id:
            continue
        if "email" in payload and existing_user.email.lower() == payload["email"].lower():
            raise ValueError("email is already in use")
        if "username" in payload and existing_user.username.lower() == payload["username"].lower():
            raise ValueError("username is already in use")


@app.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("JSON object required", 400)

    user_id = data.get("user_id")
    if not isinstance(user_id, int):
        return json_error("user_id must be an integer", 400)

    user = USERS.get(user_id)
    if not user:
        return json_error("User not found", 404)

    login_user(user)
    return jsonify({"message": "Logged in", "current_user": user.to_dict()}), 200


@app.put("/api/users/<int:user_id>")
@login_required
def update_user(user_id):
    admin_error = require_admin()
    if admin_error:
        return admin_error

    target_user = USERS.get(user_id)
    if not target_user:
        return json_error("User not found", 404)

    try:
        payload = normalize_update_payload(request.get_json(silent=True))
        ensure_unique_identity_fields(user_id, payload)
    except ValueError as exc:
        return json_error(str(exc), 400)

    for field_name, value in payload.items():
        setattr(target_user, field_name, value)

    return jsonify({"message": "User updated", "user": target_user.to_dict()}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)