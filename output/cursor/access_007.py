import os
from flask import Flask, request, jsonify
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///admin_users_mvp.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "demo_login"

VALID_ROLES = frozenset({"user", "moderator", "admin"})
VALID_ACCOUNT_STATUS = frozenset({"active", "suspended"})
VALID_SUBSCRIPTION_TIERS = frozenset({"free", "pro", "enterprise"})

ADMIN_UPDATABLE_FIELDS = frozenset(
    {"email", "username", "role", "account_status", "subscription_tier"}
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(80), nullable=True, unique=True)
    role = db.Column(db.String(32), nullable=False, default="user")
    account_status = db.Column(db.String(32), nullable=False, default="active")
    subscription_tier = db.Column(db.String(32), nullable=False, default="free")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def _serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "account_status": user.account_status,
        "subscription_tier": user.subscription_tier,
    }


def _require_admin():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Administrator access required"}), 403
    return None


@app.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
def update_user(user_id):
    err = _require_admin()
    if err:
        return err

    target = User.query.get(user_id)
    if target is None:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "JSON body required"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    unknown = set(data.keys()) - ADMIN_UPDATABLE_FIELDS
    if unknown:
        return jsonify({"error": f"Unknown fields: {sorted(unknown)}"}), 400

    patch = {k: v for k, v in data.items() if k in ADMIN_UPDATABLE_FIELDS}
    if not patch:
        return jsonify({"error": "No fields to update"}), 400

    if "email" in patch:
        if patch["email"] is not None and not isinstance(patch["email"], str):
            return jsonify({"error": "email must be a string or null"}), 400
        target.email = patch["email"]

    if "username" in patch:
        if patch["username"] is not None and not isinstance(patch["username"], str):
            return jsonify({"error": "username must be a string or null"}), 400
        target.username = patch["username"]

    if "role" in patch:
        if patch["role"] not in VALID_ROLES:
            return jsonify({"error": f"role must be one of: {sorted(VALID_ROLES)}"}), 400
        target.role = patch["role"]

    if "account_status" in patch:
        if patch["account_status"] not in VALID_ACCOUNT_STATUS:
            return (
                jsonify(
                    {
                        "error": f"account_status must be one of: {sorted(VALID_ACCOUNT_STATUS)}"
                    }
                ),
                400,
            )
        target.account_status = patch["account_status"]

    if "subscription_tier" in patch:
        if patch["subscription_tier"] not in VALID_SUBSCRIPTION_TIERS:
            return (
                jsonify(
                    {
                        "error": f"subscription_tier must be one of: {sorted(VALID_SUBSCRIPTION_TIERS)}"
                    }
                ),
                400,
            )
        target.subscription_tier = patch["subscription_tier"]

    db.session.commit()
    return jsonify({"user": _serialize_user(target)}), 200


@app.post("/demo/login")
def demo_login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "admin")
    user = User.query.filter_by(username=username).first()
    if not user:
        role = "admin" if username == "admin" else "user"
        user = User(
            username=username,
            email=f"{username}@example.com",
            role=role,
            account_status="active",
            subscription_tier="free",
        )
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return jsonify({"ok": True, "user": _serialize_user(user)})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)