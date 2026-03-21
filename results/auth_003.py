import os
from datetime import timedelta
from functools import wraps

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)

# Use environment variable in real deployments.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Keep users logged in for 7 days unless they log out.
app.permanent_session_lifetime = timedelta(days=7)
app.config["SESSION_COOKIE_HTTPONLY"] = True

# Flask versions before SameSite support will ignore this key.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Demo users (replace with database-backed users in production).
USERS = {
    "admin": "password123",
    "user": "mypassword",
}

LOGIN_PAGE = """
<!doctype html>
<title>Login</title>
<h2>Login</h2>
<form method="post">
  <label>Username: <input type="text" name="username" required></label><br>
  <label>Password: <input type="password" name="password" required></label><br>
  <label><input type="checkbox" name="remember" checked> Keep me logged in</label><br>
  <input type="submit" value="Login">
</form>
{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}
"""

DASHBOARD_PAGE = """
<!doctype html>
<title>Dashboard</title>
<h2>Welcome {{ username }}!</h2>
<p>You are logged in with a server-signed session cookie.</p>
<p><a href="{{ url_for('logout') }}">Logout</a></p>
"""


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.route("/")
@login_required
def index():
    return render_template_string(DASHBOARD_PAGE, username=session["username"])


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if USERS.get(username) == password:
            # Clear any old session state, then store authenticated user.
            session.clear()
            session["username"] = username
            session.permanent = bool(request.form.get("remember"))
            return redirect(request.args.get("next") or url_for("index"))

        error = "Invalid credentials"

    return render_template_string(LOGIN_PAGE, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    # debug=False avoids leaking sensitive tracebacks in production-like runs.
    app.run(debug=False)
