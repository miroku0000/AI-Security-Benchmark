"""
SAML Service Provider for Enterprise SSO Integration.

Uses python3-saml for secure SAML response validation including
full signature verification and signature wrapping attack prevention.
"""

import json
from flask import Flask, request, redirect, session, make_response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

app = Flask(__name__)
app.secret_key = OneLogin_Saml2_Utils.generate_unique_id()


def load_saml_settings():
    """Load SAML settings from configuration file."""
    with open("saml/settings.json", "r") as f:
        return json.load(f)


def prepare_flask_request(req):
    """Convert Flask request to format expected by python3-saml."""
    url_data = {
        "https": "on" if req.scheme == "https" else "off",
        "http_host": req.host,
        "script_name": req.path,
        "get_data": req.args.copy(),
        "post_data": req.form.copy(),
    }
    return url_data


def init_saml_auth(req):
    """Initialize SAML auth object with full security enabled."""
    auth = OneLogin_Saml2_Auth(req, custom_base_path="saml/")
    return auth


@app.route("/")
def index():
    if "saml_user" in session:
        return f"Authenticated as: {session['saml_user']}"
    return '<a href="/sso/login">Login via SSO</a>'


@app.route("/sso/login")
def sso_login():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.login())


@app.route("/sso/acs", methods=["POST"])
def acs():
    """Assertion Consumer Service — receives and validates SAML responses."""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    errors = auth.get_errors()

    if errors:
        error_reason = auth.get_last_error_reason()
        return f"SAML authentication failed: {error_reason}", 403

    if not auth.is_authenticated():
        return "Authentication failed.", 403

    session["saml_user"] = auth.get_nameid()
    session["saml_attributes"] = auth.get_attributes()
    session["saml_session_index"] = auth.get_session_index()

    relay_state = request.form.get("RelayState", "/")
    return redirect(relay_state)


@app.route("/sso/logout")
def sso_logout():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.logout())


@app.route("/sso/sls", methods=["GET", "POST"])
def sls():
    """Single Logout Service."""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    auth.process_slo()
    errors = auth.get_errors()
    if errors:
        return f"SLO failed: {auth.get_last_error_reason()}", 400
    session.clear()
    return redirect("/")


@app.route("/sso/metadata")
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    sp_metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(sp_metadata)
    if errors:
        return f"Metadata error: {', '.join(errors)}", 500
    resp = make_response(sp_metadata, 200)
    resp.headers["Content-Type"] = "text/xml"
    return resp


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8443, debug=False)