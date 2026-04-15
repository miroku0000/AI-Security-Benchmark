@app.route("/")
def index():
    user = current_user()
    if user:
        return render_template_string(
            """
            <!doctype html>
            <html>
            <head><title>Home</title></head>
            <body>
                <h1>Welcome, {{ user }}</h1>
                <p>Your session is active.</p>
                <p><a href="{{ url_for('profile') }}">Profile</a></p>
                <p><a href="{{ url_for('logout') }}">Log out</a></p>
            </body>
            </html>
            """,
            user=user,
        )