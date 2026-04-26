from __future__ import print_function

from datetime import timedelta

from flask import Flask, request, session, redirect, url_for, render_template_string

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    from werkzeug import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True

try:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
except Exception:
    pass


USERS = {
    "alice": {
        "id": 1,
        "username": "alice",
        "password_hash": generate_password_hash("password123"),
    }
}


HOME_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Flask Session Demo</title>
</head>
<body>
    <h1>Flask Session Demo</h1>
    {% if user %}
        <p>Welcome, {{ user["username"] }}.</p>
        <p><a href="{{ url_for('dashboard') }}">Go to dashboard</a></p>
        <p><a href="{{ url_for('logout') }}">Log out</a></p>
    {% else %}
        <p>You are not logged in.</p>
        <p><a href="{{ url_for('login') }}">Log in</a></p>
    {% endif %}
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Login</title>
</head>
<body>
    <h1>Log in</h1>
    {% if error %}
        <p style="color: red;">{{ error }}</p>
    {% endif %}
    <form method="post">
        <p>
            <label>Username<br>
            <input type="text" name="username"></label>
        </p>
        <p>
            <label>Password<br>
            <input type="password" name="password"></label>
        </p>
        <p>
            <label>
                <input type="checkbox" name="remember" value="1" checked>
                Keep me logged in
            </label>
        </p>
        <p><button type="submit">Log in</button></p>
    </form>
    <p>Demo account: alice / password123</p>
    <p><a href="{{ url_for('index') }}">Home</a></p>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <h1>Dashboard</h1>
    <p>You are logged in as {{ user["username"] }}.</p>
    <p>Your user ID is {{ user["id"] }}.</p>
    <p><a href="{{ url_for('logout') }}">Log out</a></p>
    <p><a href="{{ url_for('index') }}">Home</a></p>
</body>
</html>
"""


def get_current_user():
    username = session.get("username")
    if not username:
        return None
    return USERS.get(username)


def login_required(view_func):
    def wrapped(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    wrapped.__name__ = getattr(view_func, "__name__", "wrapped_view")
    wrapped.__doc__ = getattr(view_func, "__doc__", None)
    return wrapped


@app.route("/")
def index():
    return render_template_string(HOME_TEMPLATE, user=get_current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "1"

        user = USERS.get(username)
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid username or password."
        else:
            session.clear()
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            session.permanent = remember
            return redirect(url_for("dashboard"))

    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE, user=get_current_user())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)