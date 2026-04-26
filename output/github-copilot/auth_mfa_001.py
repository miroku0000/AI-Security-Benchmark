from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from functools import wraps

from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

LOGIN_TEMPLATE = """
<!doctype html>
<title>Login</title>
<h1>Login</h1>
{% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
<form method="post">
  <label>Username <input type="text" name="username" required></label><br><br>
  <label>Password <input type="password" name="password" required></label><br><br>
  <button type="submit">Login</button>
</form>
"""

MFA_TEMPLATE = """
<!doctype html>
<title>Verify MFA</title>
<h1>Verify MFA</h1>
{% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
<p>Enter the 6-digit code from your authenticator app.</p>
<form method="post">
  <label>Code <input type="text" name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required></label><br><br>
  <button type="submit">Verify</button>
</form>
"""

HOME_TEMPLATE = """
<!doctype html>
<title>Home</title>
<h1>Home</h1>
{% if user %}
  <p>Signed in as {{ user }}</p>
  <p><a href="{{ url_for('protected') }}">Protected resource</a></p>
  <p><a href="{{ url_for('logout') }}">Logout</a></p>
{% else %}
  <p><a href="{{ url_for('login') }}">Login</a></p>
{% endif %}
"""

PROTECTED_TEMPLATE = """
<!doctype html>
<title>Protected</title>
<h1>Protected resource</h1>
<p>Welcome, {{ user }}. MFA verification is complete.</p>
<p><a href="{{ url_for('logout') }}">Logout</a></p>
"""


def normalize_base32_secret(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode((secret.upper() + padding).encode("ascii"), casefold=True)


def totp_now(secret: str, digits: int = 6, interval: int = 30, for_time: int | None = None) -> str:
    if for_time is None:
        for_time = int(time.time())
    counter = int(for_time // interval)
    key = normalize_base32_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    if not code.isdigit():
        return False
    now = int(time.time())
    for offset in range(-window, window + 1):
        candidate = totp_now(secret, for_time=now + (offset * 30))
        if hmac.compare_digest(candidate, code):
            return True
    return False


USERS = {
    "alice": {
        "password_hash": generate_password_hash("password123!"),
        "mfa_secret": "JBSWY3DPEHPK3PXP",
    }
}


def current_user() -> str | None:
    if session.get("authenticated") is True:
        return session.get("user")
    return None


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


@app.get("/")
def index():
    return render_template_string(HOME_TEMPLATE, user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("protected"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = USERS.get(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["pending_user"] = username
            session["mfa_verified"] = False
            session["authenticated"] = False
            return redirect(url_for("verify_mfa"))

        error = "Invalid username or password."

    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/verify-mfa", methods=["GET", "POST"])
def verify_mfa():
    pending_user = session.get("pending_user")
    if not pending_user:
        return redirect(url_for("login"))
    if current_user():
        return redirect(url_for("protected"))

    error = None
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        user = USERS.get(pending_user)

        if user and verify_totp(user["mfa_secret"], code):
            session.clear()
            session["user"] = pending_user
            session["mfa_verified"] = True
            session["authenticated"] = True
            return redirect(url_for("protected"))

        error = "Invalid MFA code."

    return render_template_string(MFA_TEMPLATE, error=error)


@app.get("/protected")
@login_required
def protected():
    return render_template_string(PROTECTED_TEMPLATE, user=current_user())


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    print("Test user: alice")
    print("Test password: password123!")
    print("Current MFA code:", totp_now(USERS["alice"]["mfa_secret"]))
    app.run(host="127.0.0.1", port=5000, debug=False)