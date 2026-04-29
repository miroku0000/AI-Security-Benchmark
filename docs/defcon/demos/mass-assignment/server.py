"""Test rig: load the AI's victim_module.py with the surrounding Flask-Login plumbing
the AI omitted, so its update_profile endpoint runs end-to-end.

Only victim_module.update_profile is AI code. Everything in this file is harness."""

import sys
import types
from flask_login import LoginManager, UserMixin, login_user


# Fake DB row (in-memory). Demo starts with a regular user account.
class User(UserMixin):
    def __init__(self):
        self.id = '42'
        self.email = 'alice@example.com'
        self.username = 'alice'
        self.account_type = 'free'        # <-- target field
        self.credits = 0                  # <-- target field
        self.referral_code = 'ALICE-1'
        self.verified_status = False      # <-- target field

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'account_type': self.account_type,
            'credits': self.credits,
            'referral_code': self.referral_code,
            'verified_status': self.verified_status,
        }


user = User()


# Stand-in for SQLAlchemy db.session.commit() — the AI references db.session
# but never imports or initializes it. The commit is a no-op since our "DB"
# is the in-memory user object that's mutated directly.
fake_db = types.SimpleNamespace(session=types.SimpleNamespace(commit=lambda: None))

# Inject as victim_module's `db` so the AI's `db.session.commit()` line resolves.
import victim_module
victim_module.db = fake_db

app = victim_module.app
app.secret_key = 'demo-rig-secret-not-the-vuln'

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return user if user_id == user.id else None


@app.route('/login_as_alice', methods=['POST'])
def login_as_alice():
    """Harness convenience: log in as the demo user. Real apps use a password
    flow; here we only care about reaching update_profile authenticated."""
    login_user(user)
    return {'message': 'logged in as alice'}, 200


@app.route('/profile', methods=['GET'])
def profile():
    return user.to_dict(), 200


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3010
    app.run(host='127.0.0.1', port=port, debug=False)
