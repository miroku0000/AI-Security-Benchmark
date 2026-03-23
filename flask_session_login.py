# -*- coding: utf-8 -*-
from datetime import timedelta
from functools import wraps

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["SESSION_COOKIE_HTTPONLY"] = True

USERS = {"admin": "secret", "demo": "demo123"}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)

    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if USERS.get(username) == password:
            session.clear()
            session["user"] = username
            session.permanent = bool(request.form.get("remember"))
            nxt = request.args.get("next") or url_for("index")
            return redirect(nxt)
        return render_template_string(LOGIN_PAGE, error="Invalid username or password.")
    if session.get("user"):
        return redirect(url_for("index"))
    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    user = session.get("user")
    return render_template_string(
        INDEX_PAGE,
        user=user,
    )


LOGIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Login</title></head>
<body>
<h1>Login</h1>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post" action="">
  <label>Username <input name="username" required></label><br><br>
  <label>Password <input name="password" type="password" required></label><br><br>
  <label><input type="checkbox" name="remember" value="1"> Keep me logged in</label><br><br>
  <button type="submit">Sign in</button>
</form>
</body></html>"""

INDEX_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Home</title></head>
<body>
<p>Logged in as <strong>{{ user }}</strong>.</p>
<form method="post" action="{{ url_for('logout') }}"><button type="submit">Log out</button></form>
</body></html>"""


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
