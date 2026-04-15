@app.route("/oidc/callback")
def oidc_callback():
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Completing Sign-In</title>
  </head>
  <body>
    <p>Completing sign-in...</p>
    <script>
      (function () {{
        const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : '';
        const params = new URLSearchParams(hash);
        const idToken = params.get('id_token');
        const state = params.get('state');
        const error = params.get('error');
        const errorDescription = params.get('error_description');