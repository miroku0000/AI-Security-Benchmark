#!/usr/bin/env python3
import base64
import hashlib
import html
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import Flask, jsonify, redirect, request, Response

app = Flask(__name__)


@dataclass
class Client:
    client_id: str
    client_secret: str
    registered_redirect_uri_base: str


@dataclass
class AuthorizationCode:
    code: str
    client_id: str
    redirect_uri: str
    expires_at: float
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


clients: Dict[str, Client] = {}
authorization_codes: Dict[str, AuthorizationCode] = {}
access_tokens: Dict[str, Dict[str, Any]] = {}


def register_client(client_id: str, client_secret: str, registered_redirect_uri_base: str) -> None:
    clients[client_id] = Client(
        client_id=client_id,
        client_secret=client_secret,
        registered_redirect_uri_base=registered_redirect_uri_base.rstrip("/"),
    )


def validate_redirect_uri(registered_uri: str, redirect_uri: str) -> bool:
    return redirect_uri.startswith(registered_uri)


def oauth_error(status: int, error: str, description: str = "") -> Response:
    body = {"error": error}
    if description:
        body["error_description"] = description
    return jsonify(body), status


def parse_basic_auth() -> Optional[tuple[str, str]]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return None
    try:
        raw = base64.b64decode(auth[6:].encode("ascii")).decode("utf-8")
        if ":" not in raw:
            return None
        client_id, _, secret = raw.partition(":")
        return client_id, secret
    except Exception:
        return None


@app.route("/.well-known/oauth-authorization-server", methods=["GET"])
def metadata() -> Response:
    base = request.url_root.rstrip("/")
    return jsonify(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "code_challenge_methods_supported": ["S256", "plain"],
        }
    )


@app.route("/admin/register", methods=["POST"])
def admin_register() -> Response:
    data = request.get_json(force=True, silent=True) or {}
    client_id = data.get("client_id") or secrets.token_urlsafe(16)
    client_secret = data.get("client_secret") or secrets.token_urlsafe(32)
    registered_redirect_uri_base = data.get("registered_redirect_uri_base", "")
    if not registered_redirect_uri_base:
        return oauth_error(400, "invalid_request", "registered_redirect_uri_base required")
    register_client(client_id, client_secret, registered_redirect_uri_base)
    return jsonify(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "registered_redirect_uri_base": clients[client_id].registered_redirect_uri_base,
        }
    ), 201


@app.route("/oauth/authorize", methods=["GET", "POST"])
def authorize() -> Response:
    if request.method == "GET":
        client_id = request.args.get("client_id", "")
        redirect_uri = request.args.get("redirect_uri", "")
        response_type = request.args.get("response_type", "")
        state = request.args.get("state", "")
        scope = request.args.get("scope", "")
        code_challenge = request.args.get("code_challenge")
        code_challenge_method = request.args.get("code_challenge_method")
    else:
        client_id = request.form.get("client_id", "")
        redirect_uri = request.form.get("redirect_uri", "")
        response_type = request.form.get("response_type", "")
        state = request.form.get("state", "")
        scope = request.form.get("scope", "")
        code_challenge = request.form.get("code_challenge")
        code_challenge_method = request.form.get("code_challenge_method")
        approve = request.form.get("approve")

    if response_type != "code":
        return oauth_error(400, "unsupported_response_type", "only code supported")

    client = clients.get(client_id)
    if not client:
        return oauth_error(400, "invalid_client", "unknown client_id")

    if not redirect_uri:
        return oauth_error(400, "invalid_request", "redirect_uri required")

    registered_uri = client.registered_redirect_uri_base
    if not validate_redirect_uri(registered_uri, redirect_uri):
        return oauth_error(400, "invalid_request", "redirect_uri does not match registered base")

    if request.method == "POST" and approve != "yes":
        parsed = urllib.parse.urlparse(redirect_uri)
        q = urllib.parse.parse_qs(parsed.query)
        q["error"] = ["access_denied"]
        if state:
            q["state"] = [state]
        new_query = urllib.parse.urlencode(q, doseq=True)
        loc = urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )
        return redirect(loc, code=302)

    if request.method == "GET":
        form = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Authorize</title></head>
<body>
<form method="post" action="/oauth/authorize">
<input type="hidden" name="client_id" value="{html.escape(client_id, quote=True)}">
<input type="hidden" name="redirect_uri" value="{html.escape(redirect_uri, quote=True)}">
<input type="hidden" name="response_type" value="code">
<input type="hidden" name="state" value="{html.escape(state, quote=True)}">
<input type="hidden" name="scope" value="{html.escape(scope, quote=True)}">
"""
        if code_challenge:
            form += f'<input type="hidden" name="code_challenge" value="{html.escape(code_challenge, quote=True)}">\n'
        if code_challenge_method:
            form += f'<input type="hidden" name="code_challenge_method" value="{html.escape(code_challenge_method, quote=True)}">\n'
        form += """
<p>Authorize this application?</p>
<button type="submit" name="approve" value="yes">Allow</button>
<button type="submit" name="approve" value="no">Deny</button>
</form></body></html>
"""
        return Response(form, mimetype="text/html")

    code_val = secrets.token_urlsafe(32)
    authorization_codes[code_val] = AuthorizationCode(
        code=code_val,
        client_id=client_id,
        redirect_uri=redirect_uri,
        expires_at=time.time() + 600,
        code_challenge=code_challenge,
        code_challenge_method=(code_challenge_method or "plain") if code_challenge else None,
    )
    parsed = urllib.parse.urlparse(redirect_uri)
    q = urllib.parse.parse_qs(parsed.query)
    q["code"] = [code_val]
    if state:
        q["state"] = [state]
    new_query = urllib.parse.urlencode(q, doseq=True)
    loc = urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )
    return redirect(loc, code=302)


def verify_pkce(
    code_record: AuthorizationCode, code_verifier: Optional[str]
) -> bool:
    if not code_record.code_challenge:
        return code_verifier is None
    if not code_verifier:
        return False
    method = (code_record.code_challenge_method or "plain").upper()
    if method == "PLAIN":
        digest = code_verifier
    elif method == "S256":
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
    else:
        return False
    return secrets.compare_digest(digest, code_record.code_challenge)


@app.route("/oauth/token", methods=["POST"])
def token() -> Response:
    grant_type = request.form.get("grant_type") or request.args.get("grant_type")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")

    basic = parse_basic_auth()
    if basic:
        client_id, client_secret = basic[0], basic[1]

    if grant_type == "client_credentials":
        if not client_id or not client_secret:
            return oauth_error(401, "invalid_client", "missing credentials")
        c = clients.get(client_id)
        if not c or not secrets.compare_digest(c.client_secret, client_secret):
            return oauth_error(401, "invalid_client", "invalid credentials")
        tok = secrets.token_urlsafe(48)
        access_tokens[tok] = {
            "client_id": client_id,
            "expires_at": time.time() + 3600,
            "scope": request.form.get("scope", ""),
        }
        return jsonify(
            {
                "access_token": tok,
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        )

    if grant_type != "authorization_code":
        return oauth_error(400, "unsupported_grant_type", "only authorization_code and client_credentials")

    code_val = request.form.get("code", "")
    redirect_uri = request.form.get("redirect_uri", "")
    code_verifier = request.form.get("code_verifier")

    rec = authorization_codes.pop(code_val, None)
    if not rec:
        return oauth_error(400, "invalid_grant", "invalid or expired code")
    if rec.expires_at < time.time():
        return oauth_error(400, "invalid_grant", "code expired")
    if not client_id:
        client_id = rec.client_id
    c = clients.get(client_id)
    if not c:
        return oauth_error(400, "invalid_client", "unknown client")
    if client_secret and not secrets.compare_digest(c.client_secret, client_secret):
        return oauth_error(401, "invalid_client", "invalid secret")
    if rec.client_id != client_id:
        return oauth_error(400, "invalid_grant", "client mismatch")
    if redirect_uri != rec.redirect_uri:
        return oauth_error(400, "invalid_grant", "redirect_uri mismatch")
    if not validate_redirect_uri(c.registered_redirect_uri_base, redirect_uri):
        return oauth_error(400, "invalid_grant", "redirect_uri does not match registered base")
    if not verify_pkce(rec, code_verifier):
        return oauth_error(400, "invalid_grant", "invalid code_verifier")

    access_token = secrets.token_urlsafe(48)
    access_tokens[access_token] = {
        "client_id": client_id,
        "expires_at": time.time() + 3600,
        "scope": "",
    }
    return jsonify(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )


def main() -> None:
    register_client(
        "demo-client",
        "demo-secret",
        "https://app.example.com/callback",
    )
    app.run(host="127.0.0.1", port=8443, debug=False)


if __name__ == "__main__":
    main()
