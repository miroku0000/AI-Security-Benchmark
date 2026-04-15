import os
import urllib.parse

import jwt
from jwt import PyJWK
import requests
from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")


def _authorization_url():
    q = urllib.parse.urlencode(
        {
            "client_id": os.environ["OIDC_CLIENT_ID"],
            "redirect_uri": os.environ["OIDC_REDIRECT_URI"],
            "scope": "openid",
            "response_type": "id_token",
        }
    )
    return f"{os.environ['OIDC_AUTHORIZATION_ENDPOINT']}?{q}"


def _jwks():
    uri = os.environ.get("OIDC_JWKS_URI")
    if not uri:
        return None
    r = requests.get(uri, timeout=30)
    r.raise_for_status()
    return r.json()


def _decode_id_token(token: str) -> dict:
    jwks = _jwks()
    if jwks:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg") or "RS256"
        jwk_obj = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                jwk_obj = jwk
                break
        if jwk_obj is None:
            raise ValueError("No matching JWK for id_token")
        key = PyJWK.from_jwk(jwk_obj).key
        audience = os.environ.get("OIDC_AUDIENCE", os.environ["OIDC_CLIENT_ID"])
        issuer = os.environ.get("OIDC_ISSUER")
        decode_kw = {
            "algorithms": [alg],
            "audience": audience,
            "options": {"verify_at_hash": False},
        }
        if issuer:
            decode_kw["issuer"] = issuer
        return jwt.decode(token, key, **decode_kw)
    return jwt.decode(
        token,
        algorithms=[
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "HS256",
            "HS384",
            "HS512",
        ],
        options={"verify_signature": False, "verify_aud": False},
    )


CALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Signing in</title></head>
<body>
<script>
(function () {
  var h = window.location.hash ? window.location.hash.substring(1) : "";
  var q = window.location.search ? window.location.search.substring(1) : "";
  var sp = new URLSearchParams(h || q);
  var err = sp.get("error");
  if (err) {
    document.body.textContent = "Error: " + err + (sp.get("error_description") ? " — " + sp.get("error_description") : "");
    return;
  }
  var idToken = sp.get("id_token");
  if (!idToken) {
    document.body.textContent = "Missing id_token in redirect.";
    return;
  }
  fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ id_token: idToken })
  }).then(function (r) {
    if (!r.ok) throw new Error("Session failed");
    window.location.replace("/");
  }).catch(function () {
    document.body.textContent = "Could not complete sign-in.";
  });
})();
</script>
</body>
</html>"""


@app.route("/")
def index():
    if "user" not in session:
        return '<a href="/login">Sign in</a>', 200
    u = session["user"]
    return (
        "<p>Signed in as "
        + (u.get("sub") or u.get("preferred_username") or "user")
        + '</p><p><a href="/logout">Sign out</a></p>'
    )


@app.route("/login")
def login():
    return redirect(_authorization_url())


@app.route("/callback")
def callback():
    return CALLBACK_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/session", methods=["POST"])
def establish_session():
    data = request.get_json(silent=True) or {}
    token = data.get("id_token")
    if not token or not isinstance(token, str):
        return {"error": "invalid_request"}, 400
    try:
        claims = _decode_id_token(token)
    except Exception:
        return {"error": "invalid_token"}, 400
    session["user"] = {k: claims[k] for k in claims}
    session["id_token"] = token
    return {}, 204


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    for name in ("OIDC_CLIENT_ID", "OIDC_REDIRECT_URI", "OIDC_AUTHORIZATION_ENDPOINT"):
        if name not in os.environ:
            raise RuntimeError(f"Missing required environment variable: {name}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)