from flask import Flask, jsonify, request
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id, email, username, account_type, credits, referral_code, verified_status):
        self.id = user_id
        self.email = email
        self.username = username
        self.account_type = account_type
        self.credits = credits
        self.referral_code = referral_code
        self.verified_status = verified_status


USERS = {
    1: User(1, "a@example.com", "alice", "free", 10, "REF123", False),
}


@login_manager.user_loader
def load_user(user_id):
    return USERS.get(int(user_id))


ALLOWED = frozenset(
    {"email", "username", "account_type", "credits", "referral_code", "verified_status"}
)


def user_to_dict(u):
    return {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "account_type": u.account_type,
        "credits": u.credits,
        "referral_code": u.referral_code,
        "verified_status": u.verified_status,
    }


@app.route("/api/login", methods=["POST"])
def login():
    login_user(USERS[1])
    return jsonify({"ok": True})


@app.route("/api/profile", methods=["PATCH"])
@login_required
def update_profile():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "JSON body required"}), 400
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object required"}), 400

    updates = {k: v for k, v in body.items() if k in ALLOWED}
    unknown = set(body) - ALLOWED
    if unknown:
        return jsonify({"error": "Unknown fields", "fields": sorted(unknown)}), 400
    if not updates:
        return jsonify({"error": "No updatable fields provided"}), 400

    for key, value in updates.items():
        if key == "credits":
            if not isinstance(value, int) or isinstance(value, bool):
                return jsonify({"error": "credits must be an integer"}), 400
        elif key == "verified_status":
            if not isinstance(value, bool):
                return jsonify({"error": "verified_status must be a boolean"}), 400
        elif key in ("email", "username", "account_type", "referral_code"):
            if not isinstance(value, str):
                return jsonify({"error": f"{key} must be a string"}), 400
        setattr(current_user, key, value)

    return jsonify({"user": user_to_dict(current_user)})


if __name__ == "__main__":
    app.run(debug=True)