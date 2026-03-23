"""Login redirect: send users to their intended destination after authentication."""

from __future__ import annotations

import secrets
from urllib.parse import urlparse, urljoin

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Simple in-memory user store for demo only
_USERS = {"alice": "secret123"}


def _is_safe_redirect_url(target: str, host: str) -> bool:
    if not target or not target.startswith("/"):
        return False
    ref_url = urlparse(urljoin(request.host_url, target))
    return ref_url.scheme in ("", "http", "https") and ref_url.netloc == host


def get_post_login_redirect(fallback_endpoint: str = "index") -> str:
    next_url = session.pop("next_url", None)
    if next_url and _is_safe_redirect_url(next_url, request.host):
        return next_url
    return url_for(fallback_endpoint)


@app.route("/")
def index():
    user = session.get("user")
    return render_template_string(
        """
        <!doctype html>
        <html><body>
        {% if user %}
          <p>Logged in as {{ user }}.</p>
          <p><a href="{{ url_for('logout') }}">Log out</a></p>
        {% else %}
          <p><a href="{{ url_for('login', next=request.path) }}">Log in</a></p>
        {% endif %}
        </body></html>
        """,
        user=user,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    next_param = request.args.get("next") or request.form.get("next") or ""
    if next_param and _is_safe_redirect_url(next_param, request.host):
        session["next_url"] = next_param

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username in _USERS and _USERS[username] == password:
            session["user"] = username
            return redirect(get_post_login_redirect("index"))
        return render_template_string(
            """
            <!doctype html>
            <html><body>
            <p>Invalid credentials.</p>
            <form method="post">
              <input type="hidden" name="next" value="{{ next }}">
              <label>Username <input name="username"></label><br>
              <label>Password <input name="password" type="password"></label><br>
              <button type="submit">Log in</button>
            </form>
            </body></html>
            """,
            next=next_param,
        )

    return render_template_string(
        """
        <!doctype html>
        <html><body>
        <form method="post">
          <input type="hidden" name="next" value="{{ next }}">
          <label>Username <input name="username"></label><br>
          <label>Password <input name="password" type="password"></label><br>
          <button type="submit">Log in</button>
        </form>
        </body></html>
        """,
        next=next_param,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/protected")
def protected():
    if not session.get("user"):
        return redirect(url_for("login", next=request.path))
    return "Protected content"


if __name__ == "__main__":
    app.run(debug=True)
