import os
from flask import Flask, request, jsonify
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///profile_mvp.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "demo_login"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    account_type = db.Column(db.String(32), nullable=True, default="free")
    credits = db.Column(db.Integer, nullable=False, default=0)
    referral_code = db.Column(db.String(64), nullable=True)
    verified_status = db.Column(db.Boolean, nullable=False, default=False)


ALLOWED_PROFILE_FIELDS = frozenset(
    {"email", "username", "account_type", "credits", "referral_code", "verified_status"}
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def _serialize_user(user):
    return {
        "email": user.email,
        "username": user.username,
        "account_type": user.account_type,
        "credits": user.credits,
        "referral_code": user.referral_code,
        "verified_status": user.verified_status,
    }


@app.route("/api/profile", methods=["PATCH"])
@login_required
def update_profile():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "JSON body required"}), 400
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    patch = {k: v for k, v in data.items() if k in ALLOWED_PROFILE_FIELDS}
    if not patch:
        return jsonify({"error": "No valid fields to update"}), 400

    if "credits" in patch:
        try:
            patch["credits"] = int(patch["credits"])
        except (TypeError, ValueError):
            return jsonify({"error": "credits must be an integer"}), 400

    for key, value in patch.items():
        setattr(current_user, key, value)

    db.session.commit()
    return jsonify({"user": _serialize_user(current_user)}), 200


@app.post("/demo/login")
def demo_login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "demo")
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, email=f"{username}@example.com")
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