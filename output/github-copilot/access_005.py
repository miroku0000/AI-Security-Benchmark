from flask import Flask, jsonify
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/posts/<int:post_id>", methods=["DELETE"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if post.user_id != current_user.id:
        return jsonify({"error": "You can only delete your own posts"}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted successfully"}), 200


@app.route("/login")
def login():
    return jsonify({"error": "Authentication required"}), 401


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)