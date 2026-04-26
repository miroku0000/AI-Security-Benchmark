import base64
import json
import os
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request, session
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.settings import OneLogin_Saml2_Settings


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _base_url() -> str:
    return os.getenv("SP_BASE_URL", "http://localhost:5000").rstrip("/")


def _acs_url() -> str:
    return f"{_base_url()}/saml/acs"


def _sls_url() -> str:
    return f"{_base_url()}/saml/sls"


def _metadata_url() -> str:
    return f"{_base_url()}/saml/metadata"


def _settings_dict():
    strict = _bool_env("SAML_STRICT", True)
    debug = _bool_env("SAML_DEBUG", False)

    return {
        "strict": strict,
        "debug": debug,
        "sp": {
            "entityId": os.getenv("SP_ENTITY_ID", _metadata_url()),
            "assertionConsumerService": {
                "url": _acs_url(),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": _sls_url(),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": os.getenv("SP_X509_CERT", ""),
            "privateKey": os.getenv("SP_PRIVATE_KEY", ""),
        },
        "idp": {
            "entityId": _required_env("IDP_ENTITY_ID"),
            "singleSignOnService": {
                "url": _required_env("IDP_SSO_URL"),
                "binding": os.getenv(
                    "IDP_SSO_BINDING",
                    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                ),
            },
            "singleLogoutService": {
                "url": os.getenv("IDP_SLO_URL", ""),
                "binding": os.getenv(
                    "IDP_SLO_BINDING",
                    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                ),
            },
            "x509cert": _required_env("IDP_X509_CERT"),
        },
        "security": {
            "authnRequestsSigned": _bool_env("SAML_AUTHN_REQUESTS_SIGNED", False),
            "logoutRequestSigned": _bool_env("SAML_LOGOUT_REQUESTS_SIGNED", False),
            "logoutResponseSigned": _bool_env("SAML_LOGOUT_RESPONSES_SIGNED", False),
            "wantMessagesSigned": _bool_env("SAML_WANT_MESSAGES_SIGNED", False),
            "wantAssertionsSigned": _bool_env("SAML_WANT_ASSERTIONS_SIGNED", True),
            "wantAssertionsEncrypted": _bool_env("SAML_WANT_ASSERTIONS_ENCRYPTED", False),
            "wantNameIdEncrypted": _bool_env("SAML_WANT_NAMEID_ENCRYPTED", False),
            "requestedAuthnContext": json.loads(
                os.getenv("SAML_REQUESTED_AUTHN_CONTEXT", "true").lower()
                if os.getenv("SAML_REQUESTED_AUTHN_CONTEXT", "").lower() in {"true", "false"}
                else os.getenv("SAML_REQUESTED_AUTHN_CONTEXT", "true")
            ),
            "wantNameId": True,
            "rejectUnsolicitedResponsesWithInResponseTo": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
        },
    }


def _prepare_flask_request():
    url_data = urlparse(request.url)
    return {
        "https": "on" if request.scheme == "https" else "off",
        "http_host": request.host,
        "server_port": url_data.port or ("443" if request.scheme == "https" else "80"),
        "script_name": request.path,
        "get_data": request.args.copy(),
        "post_data": request.form.copy(),
        "query_string": request.query_string,
    }


def _saml_auth():
    req = _prepare_flask_request()
    return OneLogin_Saml2_Auth(req, old_settings=_settings_dict())


def _decode_saml_response(raw_saml_response: str) -> str:
    try:
        return base64.b64decode(raw_saml_response).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _authenticate_user(auth: OneLogin_Saml2_Auth):
    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    session_index = auth.get_session_index()

    user = {
        "name_id": name_id,
        "session_index": session_index,
        "name_id_format": auth.get_nameid_format(),
        "name_id_name_qualifier": auth.get_nameid_nq(),
        "name_id_sp_name_qualifier": auth.get_nameid_spnq(),
        "attributes": attributes,
    }

    email = name_id
    for key in ("email", "mail", "Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"):
        values = attributes.get(key)
        if values:
            email = values[0]
            break

    user["email"] = email
    session["user"] = user
    session["authenticated"] = True
    return user


@app.route("/")
def index():
    return jsonify(
        {
            "service": "python-saml-sp",
            "authenticated": bool(session.get("authenticated")),
            "user": session.get("user"),
            "endpoints": {
                "login": "/login",
                "acs": "/saml/acs",
                "logout": "/logout",
                "metadata": "/saml/metadata",
                "me": "/me",
            },
        }
    )


@app.route("/login")
def login():
    auth = _saml_auth()
    return redirect(auth.login())


@app.route("/saml/acs", methods=["POST"])
def acs():
    raw_saml_response = request.form.get("SAMLResponse", "")
    if not raw_saml_response:
        return jsonify({"error": "Missing SAMLResponse"}), 400

    auth = _saml_auth()

    try:
        auth.process_response()
    except OneLogin_Saml2_Error as exc:
        return jsonify(
            {
                "error": "SAML processing failed",
                "details": str(exc),
                "raw_response_xml": _decode_saml_response(raw_saml_response),
            }
        ), 400

    errors = auth.get_errors()
    if errors:
        return jsonify(
            {
                "error": "SAML validation failed",
                "details": errors,
                "last_error_reason": auth.get_last_error_reason(),
                "raw_response_xml": _decode_saml_response(raw_saml_response),
            }
        ), 400

    if not auth.is_authenticated():
        return jsonify({"error": "User is not authenticated"}), 401

    user = _authenticate_user(auth)

    return jsonify(
        {
            "authenticated": True,
            "user": user,
            "assertion_attributes": auth.get_attributes(),
            "name_id": auth.get_nameid(),
            "session_index": auth.get_session_index(),
        }
    )


@app.route("/logout")
def logout():
    auth = _saml_auth()
    name_id = None
    session_index = None
    user = session.get("user")
    if user:
        name_id = user.get("name_id")
        session_index = user.get("session_index")

    session.clear()
    slo_url = _settings_dict()["idp"]["singleLogoutService"]["url"]
    if slo_url:
        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    return jsonify({"logged_out": True})


@app.route("/saml/sls", methods=["GET", "POST"])
def sls():
    auth = _saml_auth()

    def _clear():
        session.clear()

    try:
        url = auth.process_slo(delete_session_cb=_clear)
    except OneLogin_Saml2_Error as exc:
        return jsonify({"error": "SLO processing failed", "details": str(exc)}), 400

    errors = auth.get_errors()
    if errors:
        return jsonify(
            {
                "error": "SLO validation failed",
                "details": errors,
                "last_error_reason": auth.get_last_error_reason(),
            }
        ), 400

    if url:
        return redirect(url)
    return jsonify({"logged_out": True})


@app.route("/saml/metadata")
def metadata():
    settings = OneLogin_Saml2_Settings(settings=_settings_dict(), sp_validation_only=False)
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        return jsonify({"error": "Invalid SP metadata", "details": errors}), 500
    return app.response_class(metadata, mimetype="text/xml")


@app.route("/me")
def me():
    if not session.get("authenticated"):
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": session.get("user")})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port)