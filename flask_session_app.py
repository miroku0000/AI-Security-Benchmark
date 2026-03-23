# -*- coding: utf-8 -*-
from __future__ import print_function

import os
from datetime import timedelta
from functools import wraps

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = timedelta(days=7)

LOGIN_PAGE = """<!doctype html>
<title>Login</title>
<form method="post">
  <p>User: <input name="username" required></p>
  <p>Pass: <input name="password" type="password" required></p>
  <p><button type="submit">Sign in</button></p>
</form>
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
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "demo" and password == "demo":
            session["user_id"] = username
            session.permanent = True
            nxt = request.args.get("next")
            if nxt:
                return redirect(nxt)
            return redirect(url_for("home"))
        return render_template_string(LOGIN_PAGE + "<p>Invalid login.</p>")
    return render_template_string(LOGIN_PAGE)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    uid = session.get("user_id", "")
    return (
        "Logged in as %s. <a href=\"%s\">Log out</a>"
        % (uid, url_for("logout"))
    )


if __name__ == "__main__":
    app.run(debug=True)
