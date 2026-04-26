from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

USERS = {
    "alice": "wonderland",
    "bob": "builder",
}


def is_authenticated() -> bool:
    return "user" in session


def is_safe_redirect_target(target: str | None) -> bool:
    if not target:
        return False
    host_url = request.host_url
    test_url = urlparse(urljoin(host_url, target))
    ref_url = urlparse(host_url)
    return test_url.scheme in {"http", "https"} and test_url.netloc == ref_url.netloc


def redirect_after_login(default_endpoint: str = "dashboard"):
    target = session.pop("next_url", None) or request.args.get("next")
    if is_safe_redirect_target(target):
        return redirect(target)
    return redirect(url_for(default_endpoint))


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            next_url = request.full_path if request.query_string else request.path
            session["next_url"] = next_url
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


@app.route("/")
def home():
    user = session.get("user")
    return render_template_string(
        """
        <h1>Home</h1>
        {% if user %}
            <p>Signed in as <strong>{{ user }}</strong></p>
            <p><a href="{{ url_for('dashboard') }}">Dashboard</a></p>
            <p><a href="{{ url_for('reports') }}">Reports</a></p>
            <p><a href="{{ url_for('settings') }}">Settings</a></p>
            <p><a href="{{ url_for('logout') }}">Logout</a></p>
        {% else %}
            <p><a href="{{ url_for('login') }}">Login</a></p>
            <p><a href="{{ url_for('reports') }}">Try Reports (protected)</a></p>
            <p><a href="{{ url_for('settings') }}">Try Settings (protected)</a></p>
        {% endif %}
        """,
        user=user,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if USERS.get(username) == password:
            session["user"] = username
            return redirect_after_login()
        error = "Invalid username or password."

    return render_template_string(
        """
        <h1>Login</h1>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        <form method="post">
            <label>Username <input name="username" autocomplete="username"></label><br><br>
            <label>Password <input name="password" type="password" autocomplete="current-password"></label><br><br>
            <button type="submit">Sign in</button>
        </form>
        <p>Try: alice / wonderland</p>
        <p><a href="{{ url_for('home') }}">Back home</a></p>
        """,
        error=error,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(
        """
        <h1>Dashboard</h1>
        <p>Welcome, {{ user }}.</p>
        <p><a href="{{ url_for('reports') }}">Reports</a></p>
        <p><a href="{{ url_for('settings') }}">Settings</a></p>
        <p><a href="{{ url_for('logout') }}">Logout</a></p>
        """,
        user=session["user"],
    )


@app.route("/reports")
@login_required
def reports():
    return render_template_string(
        """
        <h1>Reports</h1>
        <p>You were redirected here after login if this was your intended destination.</p>
        <p><a href="{{ url_for('dashboard') }}">Dashboard</a></p>
        """,
    )


@app.route("/settings")
@login_required
def settings():
    return render_template_string(
        """
        <h1>Settings</h1>
        <p>You were redirected here after login if this was your intended destination.</p>
        <p><a href="{{ url_for('dashboard') }}">Dashboard</a></p>
        """,
    )


if __name__ == "__main__":
    app.run(debug=True)