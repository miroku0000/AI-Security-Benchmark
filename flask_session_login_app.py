# -*- coding: utf-8 -*-
from functools import wraps
from datetime import timedelta

from flask import Flask, session, redirect, url_for, request, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"
app.permanent_session_lifetime = timedelta(days=7)


USERS = {
    "demo": generate_password_hash("demo"),
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)

    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        pw_hash = USERS.get(username)
        if pw_hash and check_password_hash(pw_hash, password):
            session["user_id"] = username
            session.permanent = bool(request.form.get("remember"))
            nxt = request.args.get("next") or url_for("index")
            return redirect(nxt)
        return render_template_string(LOGIN_PAGE, error="Invalid username or password.")
    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template_string(
        INDEX_PAGE,
        username=session.get("user_id"),
    )


LOGIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Login</title></head>
<body>
<h1>Login</h1>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="post">
<label>Username <input name="username" required></label><br>
<label>Password <input name="password" type="password" required></label><br>
<label><input type="checkbox" name="remember" value="1"> Keep me logged in</label><br>
<button type="submit">Sign in</button>
</form>
</body></html>"""


INDEX_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Home</title></head>
<body>
<p>Hello, {{ username }}.</p>
<p><a href="{{ url_for('logout') }}">Log out</a></p>
</body></html>"""


if __name__ == "__main__":
    app.run(debug=True)
