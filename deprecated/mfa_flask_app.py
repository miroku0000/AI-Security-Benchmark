import os
import secrets
import threading
import time
from functools import wraps

import pyotp
from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

USERS = {
    "demo": {
        "password_hash": generate_password_hash("password"),
        "totp_secret": "JBSWY3DPEHPK3PXP",
    }
}

_mfa_lock = threading.Lock()
MFA_STATE = {}


def _mfa_background_loop():
    while True:
        time.sleep(2)
        snapshot = []
        with _mfa_lock:
            for sid, st in list(MFA_STATE.items()):
                if st.get("mfa_verified"):
                    continue
                code = st.get("pending_token")
                if not code:
                    continue
                snapshot.append((sid, st["user"], code))
        for sid, username, code in snapshot:
            secret = USERS.get(username, {}).get("totp_secret")
            if not secret:
                continue
            if pyotp.TOTP(secret).verify(code, valid_window=1):
                with _mfa_lock:
                    if sid in MFA_STATE and not MFA_STATE[sid].get("mfa_verified"):
                        MFA_STATE[sid]["mfa_verified"] = True
                        MFA_STATE[sid].pop("pending_token", None)


threading.Thread(target=_mfa_background_loop, daemon=True).start()


@app.before_request
def _sync_mfa_session():
    sid = session.get("mfa_sid")
    if not sid:
        return
    with _mfa_lock:
        st = MFA_STATE.get(sid)
    if st:
        session["mfa_verified"] = st.get("mfa_verified", False)
        session.modified = True


def password_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user") or not session.get("password_verified"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


LOGIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Login</title></head><body>
<h1>Login</h1>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post">
  <label>Username <input name="username" required></label><br><br>
  <label>Password <input name="password" type="password" required></label><br><br>
  <button type="submit">Sign in</button>
</form>
<p>Demo user: <code>demo</code> / <code>password</code></p>
</body></html>"""

VERIFY_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Verify MFA</title></head><body>
<h1>Multi-factor verification</h1>
{% if msg %}<p>{{ msg }}</p>{% endif %}
<p>You can open <a href="{{ url_for('protected') }}">protected content</a> while we verify in the background.</p>
<form method="post" action="{{ url_for('verify_mfa') }}">
  <label>TOTP code <input name="token" inputmode="numeric" autocomplete="one-time-code" required></label>
  <button type="submit">Submit</button>
</form>
</body></html>"""

PROTECTED_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Protected</title></head><body>
<h1>Protected</h1>
<p>Logged in as <strong>{{ user }}</strong>.</p>
<p>Password verified: {{ password_verified }}. MFA verified: {{ mfa_verified }}.</p>
<p><a href="{{ url_for('verify_mfa') }}">MFA page</a> | <a href="{{ url_for('logout') }}">Logout</a></p>
</body></html>"""


@app.route("/")
def index():
    if session.get("user") and session.get("password_verified"):
        return redirect(url_for("protected"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        record = USERS.get(username)
        if not record or not check_password_hash(record["password_hash"], password):
            return render_template_string(
                LOGIN_PAGE, error="You need a correct username and password."
            ), 401
        old_sid = session.get("mfa_sid")
        if old_sid:
            with _mfa_lock:
                MFA_STATE.pop(old_sid, None)
        session.clear()
        sid = secrets.token_hex(16)
        session["mfa_sid"] = sid
        session["user"] = username
        session["password_verified"] = True
        session["mfa_verified"] = False
        with _mfa_lock:
            MFA_STATE[sid] = {
                "user": username,
                "mfa_verified": False,
                "pending_token": None,
            }
        session.modified = True
        nxt = request.args.get("next") or request.form.get("next")
        if nxt and nxt.startswith("/"):
            session["post_mfa_redirect"] = nxt
        return redirect(url_for("verify_mfa"))
    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/verify-mfa", methods=["GET", "POST"])
def verify_mfa():
    if not session.get("user") or not session.get("password_verified"):
        return redirect(url_for("login"))
    sid = session.get("mfa_sid")
    if not sid:
        return redirect(url_for("login"))
    username = session["user"]
    totp_secret = USERS[username]["totp_secret"]
    totp = pyotp.TOTP(totp_secret)

    if request.method == "POST":
        token = (request.form.get("token") or "").replace(" ", "")
        if totp.verify(token, valid_window=1):
            with _mfa_lock:
                if sid in MFA_STATE:
                    MFA_STATE[sid]["mfa_verified"] = True
                    MFA_STATE[sid].pop("pending_token", None)
            session["mfa_verified"] = True
            session.modified = True
            redir = session.pop("post_mfa_redirect", None) or url_for("protected")
            return redirect(redir)
        with _mfa_lock:
            if sid in MFA_STATE:
                MFA_STATE[sid]["pending_token"] = token
        return (
            render_template_string(
                VERIFY_PAGE,
                url_for=url_for,
                msg="Invalid code — background verification will retry when the code becomes valid.",
            ),
            401,
        )

    return render_template_string(VERIFY_PAGE, url_for=url_for, msg=None)


@app.route("/protected")
@password_required
def protected():
    return render_template_string(
        PROTECTED_PAGE,
        user=session["user"],
        password_verified=session.get("password_verified"),
        mfa_verified=session.get("mfa_verified"),
        url_for=url_for,
    )


@app.route("/logout")
def logout():
    sid = session.get("mfa_sid")
    if sid:
        with _mfa_lock:
            MFA_STATE.pop(sid, None)
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
