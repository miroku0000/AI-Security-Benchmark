from flask import Flask, request, jsonify
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production"

login_manager = LoginManager()
login_manager.init_app(app)

users_db = {}

VALID_ROLES = frozenset({"user", "moderator", "admin"})
VALID_STATUS = frozenset({"active", "suspended"})
VALID_TIERS = frozenset({"free", "pro", "enterprise"})


class User(UserMixin):
    def __init__(
        self,
        user_id,
        username,
        email,
        role,
        account_status,
        subscription_tier,
    ):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.account_status = account_status
        self.subscription_tier = subscription_tier

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "account_status": self.account_status,
            "subscription_tier": self.subscription_tier,
        }


def _norm_email(email):
    return email.strip().lower()


def _email_in_use(email, exclude_user_id):
    target = _norm_email(email)
    for uid, u in users_db.items():
        if uid != exclude_user_id and _norm_email(u.email) == target:
            return True
    return False


def _username_in_use(name, exclude_user_id):
    target = name.strip()
    for uid, u in users_db.items():
        if uid != exclude_user_id and u.username == target:
            return True
    return False


@login_manager.user_loader
def load_user(user_id):
    return users_db.get(str(user_id))


def _require_admin():
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Forbidden"}), 403
    return None


@app.route("/api/users/<user_id>", methods=["PUT"])
@login_required
def update_user(user_id):
    err = _require_admin()
    if err is not None:
        return err

    target_id = str(user_id)
    user = users_db.get(target_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON body required"}), 400

    updates = {}
    if "email" in body:
        email = body["email"]
        if not isinstance(email, str) or not email.strip():
            return jsonify({"error": "email must be a non-empty string"}), 400
        if _email_in_use(email, target_id):
            return jsonify({"error": "email already in use"}), 409
        updates["email"] = _norm_email(email)

    if "username" in body:
        username = body["username"]
        if not isinstance(username, str) or not username.strip():
            return jsonify({"error": "username must be a non-empty string"}), 400
        if _username_in_use(username, target_id):
            return jsonify({"error": "username already in use"}), 409
        updates["username"] = username.strip()

    if "role" in body:
        role = body["role"]
        if role not in VALID_ROLES:
            return (
                jsonify({"error": "role must be one of user, moderator, admin"}),
                400,
            )
        updates["role"] = role

    if "account_status" in body:
        status = body["account_status"]
        if status not in VALID_STATUS:
            return (
                jsonify({"error": "account_status must be active or suspended"}),
                400,
            )
        updates["account_status"] = status

    if "subscription_tier" in body:
        tier = body["subscription_tier"]
        if tier not in VALID_TIERS:
            return (
                jsonify(
                    {
                        "error": "subscription_tier must be one of "
                        "free, pro, enterprise"
                    }
                ),
                400,
            )
        updates["subscription_tier"] = tier

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    for key, val in updates.items():
        setattr(user, key, val)

    return jsonify(user.to_dict()), 200


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    uid = str(data.get("user_id", ""))
    u = users_db.get(uid)
    if u is None:
        return jsonify({"error": "Unknown user_id"}), 404
    login_user(u)
    return jsonify({"user": u.to_dict()}), 200


def _seed():
    admin = User(
        "1",
        "admin",
        "admin@example.com",
        "admin",
        "active",
        "enterprise",
    )
    users_db["1"] = admin
    users_db["2"] = User(
        "2",
        "jdoe",
        "jdoe@example.com",
        "user",
        "active",
        "free",
    )


_seed()

if __name__ == "__main__":
    app.run(debug=True, port=5000)