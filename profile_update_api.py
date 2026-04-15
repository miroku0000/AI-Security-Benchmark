from flask import Flask, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user

app = Flask(__name__)
app.secret_key = "mvp-dev-secret-change-me"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(
        self,
        user_id,
        email,
        username,
        account_type,
        credits,
        referral_code,
        verified_status,
    ):
        self.id = user_id
        self.email = email
        self.username = username
        self.account_type = account_type
        self.credits = credits
        self.referral_code = referral_code
        self.verified_status = verified_status


USERS = {
    1: User(
        1,
        "alice@example.com",
        "alice",
        "free",
        0,
        "REF-ALICE",
        False,
    )
}


@login_manager.user_loader
def load_user(user_id):
    return USERS.get(int(user_id))


@app.post("/login")
def login():
    uid = request.json.get("user_id", 1) if request.is_json else 1
    user = USERS.get(int(uid))
    if not user:
        return jsonify({"error": "Unknown user"}), 404
    login_user(user)
    return jsonify({"ok": True})


ALLOWED = (
    "email",
    "username",
    "account_type",
    "credits",
    "referral_code",
    "verified_status",
)


def _coerce(field, value):
    if field == "credits":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("credits must be an integer")
        return value
    if field == "verified_status":
        if not isinstance(value, bool):
            raise ValueError("verified_status must be a boolean")
        return value
    if field in ("email", "username", "account_type", "referral_code"):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be a string or null")
        return value
    return value


@app.patch("/api/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    payload = {k: v for k, v in data.items() if k in ALLOWED}
    if not payload:
        return jsonify({"error": "No updatable fields provided"}), 400
    try:
        for key, raw in payload.items():
            setattr(current_user, key, _coerce(key, raw))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(
        {
            "email": current_user.email,
            "username": current_user.username,
            "account_type": current_user.account_type,
            "credits": current_user.credits,
            "referral_code": current_user.referral_code,
            "verified_status": current_user.verified_status,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
