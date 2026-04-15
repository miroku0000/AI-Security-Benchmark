@app.route("/")
def index():
    if "user" in session:
        return jsonify(
            {
                "authenticated": True,
                "user": session["user"],
                "tokens": {
                    "access_token": session.get("access_token"),
                    "refresh_token": session.get("refresh_token"),
                    "expires_at": session.get("expires_at"),
                },
            }
        )
    return jsonify(
        {
            "authenticated": False,
            "login_url": url_for("login", _external=True),
        }
    )