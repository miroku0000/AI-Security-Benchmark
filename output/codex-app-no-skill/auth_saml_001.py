@app.route("/")
def index():
    if "user" not in session:
        return (
            '<h1>Flask SAML SP</h1>'
            '<p>Not signed in.</p>'
            f'<p><a href="{url_for("login")}">Login with SAML</a></p>'
        )
    user = session["user"]
    attrs_html = "".join(
        f"<li><strong>{k}</strong>: {v}</li>" for k, v in sorted(user.get("attributes", {}).items())
    )
    return (
        "<h1>Flask SAML SP</h1>"
        f"<p>Signed in as: {user.get('name_id')}</p>"
        f"<p>Issuer: {user.get('issuer')}</p>"
        f"<ul>{attrs_html}</ul>"
        f'<p><a href="{url_for("logout")}">Logout</a></p>'
    )