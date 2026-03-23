@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(
        """
        <!doctype html>
        <html>
        <head>
            <title>Dashboard</title>
        </head>
        <body>
            <h1>Welcome, {{ username }}</h1>
            <p>You are logged in.</p>
            <p><a href="{{ url_for('profile') }}">Profile</a></p>
            <p><a href="{{ url_for('logout') }}">Log Out</a></p>
        </body>
        </html>
        """,
        username=session.get("user_id")
    )