from urllib.parse import urlparse, urljoin

from flask import Flask, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "change-me-in-production"


def allowed_redirect(target: str) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def login_redirect(default: str = "/") -> str:
    next_url = request.args.get("next") or session.pop("next", None)
    if next_url and allowed_redirect(next_url):
        return next_url
    return default


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        nxt = request.args.get("next")
        if nxt and allowed_redirect(nxt):
            session["next"] = nxt
        return (
            '<form method="post">'
            '<input name="username" placeholder="user"/>'
            '<input type="password" name="password" placeholder="pass"/>'
            '<button type="submit">Login</button>'
            "</form>"
        )
    if request.form.get("username") == "user" and request.form.get("password") == "pass":
        dest = login_redirect("/")
        return redirect(dest)
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    return "Dashboard"


if __name__ == "__main__":
    app.run(debug=True)