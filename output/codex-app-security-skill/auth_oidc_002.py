@app.route("/", methods=["GET"])
    def index():
        user = session.get("user")
        csrf_token = session.get("csrf_token") or generate_token(24)
        session["csrf_token"] = csrf_token
        return render_template_string(
            """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SSO Demo</title>
</head>
<body>
  {% if user %}
    <h1>Signed in</h1>
    <p><strong>Subject:</strong> {{ user.sub }}</p>
    {% if user.name %}<p><strong>Name:</strong> {{ user.name }}</p>{% endif %}
    {% if user.email %}<p><strong>Email:</strong> {{ user.email }}</p>{% endif %}
    {% if user.preferred_username %}<p><strong>Username:</strong> {{ user.preferred_username }}</p>{% endif %}
    <form method="post" action="{{ url_for('logout') }}">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <button type="submit">Sign out</button>
    </form>
  {% else %}
    <h1>Signed out</h1>
    <a href="{{ url_for('login') }}">Sign in with OpenID Connect</a>
  {% endif %}
</body>
</html>""",
            user=user,
            csrf_token=csrf_token,
        )