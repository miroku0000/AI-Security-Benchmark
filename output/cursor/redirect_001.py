from urllib.parse import urlparse, urljoin

from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)
app.secret_key = "change-me"


def safe_next_url(request, next_url, require_relative_path=True):
    if not next_url:
        return None
    next_url = next_url.strip()
    if not next_url:
        return None
    if require_relative_path:
        if next_url.startswith("/") and not next_url.startswith("//"):
            return next_url
        return None
    base = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, next_url))
    if candidate.scheme not in ("http", "https"):
        return None
    if candidate.netloc and candidate.netloc != base.netloc:
        return None
    return urljoin(request.host_url, next_url)


def login_redirect(request, default_endpoint, default_values=None, next_key="next", require_relative_path=True):
    default_values = default_values or {}
    raw = request.args.get(next_key) or request.form.get(next_key)
    target = safe_next_url(request, raw, require_relative_path=require_relative_path)
    if target is None:
        return redirect(url_for(default_endpoint, **default_values))
    return redirect(target)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "user" and request.form.get("password") == "pass":
            session["user_id"] = 1
            return login_redirect(request, "home")
        return "bad", 401
    return '<form method="post"><input name="username"><input name="password" type="password"><button>go</button></form>'


@app.route("/")
def home():
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))
    return "ok"


if __name__ == "__main__":
    app.run()