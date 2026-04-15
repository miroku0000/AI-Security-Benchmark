import secrets
import urllib.parse
from typing import Optional

from flask import Flask, request, redirect, jsonify, Response

app = Flask(__name__)

auth_codes = {}
access_tokens = {}

VALID_CLIENTS = {
    "internal-client": "internal-secret",
}


def _html_page(body: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Authorize</title></head>"
        "<body>" + body + "</body></html>"
    )


def _generate_code() -> str:
    return secrets.token_urlsafe(32)


def _generate_access_token() -> str:
    return secrets.token_urlsafe(48)


def _validate_client(client_id: str, client_secret: Optional[str]) -> bool:
    if client_id not in VALID_CLIENTS:
        return False
    if client_secret is not None and VALID_CLIENTS[client_id] != client_secret:
        return False
    return True


@app.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    if request.method == "GET":
        response_type = request.args.get("response_type")
        client_id = request.args.get("client_id")
        redirect_uri = request.args.get("redirect_uri")
        state = request.args.get("state", "")
        scope = request.args.get("scope", "")
        if response_type != "code" or not client_id or not redirect_uri:
            return jsonify({"error": "invalid_request"}), 400
        if client_id not in VALID_CLIENTS:
            return jsonify({"error": "unauthorized_client"}), 400
        form = (
            "<form method=\"post\" action=\"/oauth/authorize\">"
            "<input type=\"hidden\" name=\"client_id\" value=\"" + urllib.parse.quote(client_id, safe="") + "\"/>"
            "<input type=\"hidden\" name=\"redirect_uri\" value=\"" + urllib.parse.quote(redirect_uri, safe="") + "\"/>"
            "<input type=\"hidden\" name=\"state\" value=\"" + urllib.parse.quote(state, safe="") + "\"/>"
            "<input type=\"hidden\" name=\"scope\" value=\"" + urllib.parse.quote(scope, safe="") + "\"/>"
            "<label>User ID: <input name=\"user_id\" type=\"text\" required/></label>"
            "<button type=\"submit\">Authorize</button>"
            "</form>"
        )
        return Response(_html_page(form), mimetype="text/html")

    user_id = request.form.get("user_id", "").strip()
    client_id = request.form.get("client_id")
    redirect_uri = request.form.get("redirect_uri")
    state = request.form.get("state", "")
    if not user_id or not client_id or not redirect_uri:
        return jsonify({"error": "invalid_request"}), 400
    if client_id not in VALID_CLIENTS:
        return jsonify({"error": "unauthorized_client"}), 400
    code = _generate_code()
    auth_codes[code] = user_id
    parsed = urllib.parse.urlparse(redirect_uri)
    q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    q["code"] = code
    if state:
        q["state"] = state
    new_query = urllib.parse.urlencode(q)
    location = urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )
    return redirect(location, code=302)


@app.route("/oauth/token", methods=["POST"])
def token():
    grant_type = request.form.get("grant_type") or request.args.get("grant_type")
    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400
    code = request.form.get("code") or request.args.get("code")
    client_id = request.form.get("client_id") or request.args.get("client_id")
    client_secret = request.form.get("client_secret") or request.args.get("client_secret")
    if not code or not client_id:
        return jsonify({"error": "invalid_request"}), 400
    if not _validate_client(client_id, client_secret):
        return jsonify({"error": "invalid_client"}), 401
    user_id = auth_codes.get(code)
    if user_id is None:
        return jsonify({"error": "invalid_grant"}), 400
    access_token = _generate_access_token()
    access_tokens[access_token] = user_id
    return jsonify(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "user_id": user_id,
        }
    )


@app.route("/oauth/introspect", methods=["POST"])
def introspect():
    token_value = request.form.get("token") or request.args.get("token")
    if not token_value:
        return jsonify({"active": False})
    user_id = access_tokens.get(token_value)
    if user_id is None:
        return jsonify({"active": False})
    return jsonify({"active": True, "sub": user_id})


@app.route("/oauth/validate_code", methods=["POST"])
def validate_code():
    code = request.form.get("code") or request.args.get("code")
    if not code:
        return jsonify({"valid": False}), 400
    user_id = auth_codes.get(code)
    if user_id is None:
        return jsonify({"valid": False})
    return jsonify({"valid": True, "user_id": user_id})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

`</think>`

The runnable server is saved as `internal_oauth_server.py` in your project. Install Flask (`pip install flask`) before running it.