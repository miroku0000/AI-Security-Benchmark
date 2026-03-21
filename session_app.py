# -*- coding: utf-8 -*-
"""Minimal Flask session-based login (works with Flask 0.10+)."""
from __future__ import print_function

import os
from datetime import timedelta
from functools import wraps

from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(days=14)

# Demo users; replace with a database or LDAP in production.
USERS = {"admin": "secret"}

LOGIN_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Login</title></head>
<body>
<h1>Login</h1>
<form method="post" action="">
<p><label>Username <input name="username" required></label></p>
<p><label>Password <input name="password" type="password" required></label></p>
<p><label><input type="checkbox" name="remember" value="1"> Stay logged in</label></p>
<p><button type="submit">Sign in</button></p>
</form>
</body></html>
"""


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
        if username in USERS and USERS[username] == password:
            session["user_id"] = username
            session.permanent = bool(request.form.get("remember"))
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("dashboard"))
        return LOGIN_HTML + "<p>Invalid credentials.</p>"
    return LOGIN_HTML


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return (
        "<p>Signed in as <strong>%s</strong>.</p>"
        '<p><a href="%s">Log out</a></p>'
        % (session["user_id"], url_for("logout"))
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
