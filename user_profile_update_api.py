import os

from flask import Flask, jsonify, request
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
login_manager = LoginManager(app)


@login_manager.unauthorized_handler
def _unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


users_by_id = {}
users_by_email = {}

ALLOWED_FIELDS = frozenset(
    {"email", "username", "account_type", "credits", "referral_code", "verified_status"}
)


class User(UserMixin):
    def __init__(
        self,
        id,
        email,
        username,
        account_type,
        credits,
        referral_code,
        verified_status,
        password_hash,
    ):
        self.id = id
        self.email = email
        self.username = username
        self.account_type = account_type
        self.credits = credits
        self.referral_code = referral_code
        self.verified_status = verified_status
        self.password_hash = password_hash

    def to_public_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "account_type": self.account_type,
            "credits": self.credits,
            "referral_code": self.referral_code,
            "verified_status": self.verified_status,
        }


def _rebuild_email_index():
    users_by_email.clear()
    for u in users_by_id.values():
        users_by_email[u.email.lower()] = u


def _seed_demo_user():
    uid = 1
    u = User(
        id=uid,
        email="alice@example.com",
        username="alice",
        account_type="free",
        credits=0,
        referral_code="REF-DEMO",
        verified_status=False,
        password_hash=generate_password_hash("password"),
    )
    users_by_id[uid] = u
    _rebuild_email_index()


_seed_demo_user()


@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return users_by_id.get(int(user_id))
    except (TypeError, ValueError):
        return None


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    u = users_by_email.get(email)
    if not u or not check_password_hash(u.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401
    login_user(u)
    return jsonify(u.to_public_dict()), 200


@app.route("/api/profile", methods=["PATCH"])
@login_required
def update_profile():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "JSON body required"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    extra = set(data) - ALLOWED_FIELDS
    if extra:
        return jsonify({"error": "Unsupported fields", "fields": sorted(extra)}), 400

    u = users_by_id.get(current_user.id)
    if u is None:
        return jsonify({"error": "Unauthorized"}), 401

    if "email" in data:
        raw = data["email"]
        if raw is None:
            return jsonify({"error": "email cannot be null"}), 400
        new_email = str(raw).strip()
        if "@" not in new_email:
            return jsonify({"error": "Invalid email"}), 400
        u.email = new_email
        _rebuild_email_index()

    if "username" in data:
        raw = data["username"]
        if raw is None:
            return jsonify({"error": "username cannot be null"}), 400
        u.username = str(raw).strip()

    if "account_type" in data:
        raw = data["account_type"]
        if raw is None:
            return jsonify({"error": "account_type cannot be null"}), 400
        u.account_type = str(raw)

    if "credits" in data:
        c = data["credits"]
        if not isinstance(c, int) or isinstance(c, bool):
            return jsonify({"error": "credits must be an integer"}), 400
        if c < 0:
            return jsonify({"error": "credits must be non-negative"}), 400
        u.credits = c

    if "referral_code" in data:
        rc = data["referral_code"]
        if rc is None:
            u.referral_code = None
        else:
            u.referral_code = str(rc)

    if "verified_status" in data:
        vs = data["verified_status"]
        if not isinstance(vs, bool):
            return jsonify({"error": "verified_status must be a boolean"}), 400
        u.verified_status = vs

    return jsonify(u.to_public_dict()), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
