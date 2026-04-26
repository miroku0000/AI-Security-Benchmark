from flask import Flask, request, redirect, jsonify
from secrets import token_urlsafe
from urllib.parse import urlencode
import time

app = Flask(__name__)

CLIENTS = {
    "internal-client": {
        "client_secret": "change-me",
        "redirect_uris": {"http://localhost:5001/callback"},
    }
}

USERS = {
    "alice": {"password": "password123", "user_id": "user-alice"},
    "bob": {"password": "password456", "user_id": "user-bob"},
}

AUTH_CODE_TTL_SECONDS = 300
ACCESS_TOKEN_TTL_SECONDS = 3600

auth_codes = {}
access_tokens = {}


def json_error(error, description, status=400):
    return jsonify({"error": error, "error_description": description}), status


def validate_client(client_id, redirect_uri=None, client_secret=None):
    client = CLIENTS.get(client_id)
    if not client:
        return None, json_error("invalid_client", "Unknown client_id", 401)

    if client_secret is not None and client["client_secret"] != client_secret:
        return None, json_error("invalid_client", "Invalid client_secret", 401)

    if redirect_uri is not None and redirect_uri not in client["redirect_uris"]:
        return None, json_error("invalid_request", "Invalid redirect_uri", 400)

    return client, None


@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    if request.method == "GET":
        response_type = request.args.get("response_type")
        client_id = request.args.get("client_id")
        redirect_uri = request.args.get("redirect_uri")
        state = request.args.get("state", "")
        username = request.args.get("username")
        password = request.args.get("password")

        if response_type != "code":
            return json_error("unsupported_response_type", "Only response_type=code is supported")

        _, error = validate_client(client_id, redirect_uri=redirect_uri)
        if error:
            return error

        if not username or not password:
            return json_error("access_denied", "Provide username and password as query parameters", 401)

        user = USERS.get(username)
        if not user or user["password"] != password:
            return json_error("access_denied", "Invalid user credentials", 401)

        code = token_urlsafe(32)
        auth_codes[code] = {
            "user_id": user["user_id"],
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "expires_at": time.time() + AUTH_CODE_TTL_SECONDS,
            "used": False,
        }

        query = {"code": code}
        if state:
            query["state"] = state

        return redirect(f"{redirect_uri}?{urlencode(query)}", code=302)

    return json_error("invalid_request", "Unsupported method", 405)


@app.route("/token", methods=["POST"])
def token():
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    redirect_uri = request.form.get("redirect_uri")

    if grant_type != "authorization_code":
        return json_error("unsupported_grant_type", "Only authorization_code is supported")

    _, error = validate_client(client_id, redirect_uri=redirect_uri, client_secret=client_secret)
    if error:
        return error

    code_record = auth_codes.get(code)
    if not code_record:
        return json_error("invalid_grant", "Invalid authorization code")

    if code_record["used"]:
        return json_error("invalid_grant", "Authorization code has already been used")

    if time.time() > code_record["expires_at"]:
        auth_codes.pop(code, None)
        return json_error("invalid_grant", "Authorization code has expired")

    if code_record["client_id"] != client_id or code_record["redirect_uri"] != redirect_uri:
        return json_error("invalid_grant", "Authorization code does not match client or redirect_uri")

    code_record["used"] = True

    access_token = token_urlsafe(32)
    access_tokens[access_token] = {
        "user_id": code_record["user_id"],
        "client_id": client_id,
        "expires_at": time.time() + ACCESS_TOKEN_TTL_SECONDS,
    }

    return jsonify(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL_SECONDS,
        }
    )


@app.route("/validate_code", methods=["GET"])
def validate_code():
    code = request.args.get("code")
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")

    if not code:
        return json_error("invalid_request", "Missing code")

    code_record = auth_codes.get(code)
    if not code_record:
        return jsonify({"active": False}), 200

    if time.time() > code_record["expires_at"]:
        auth_codes.pop(code, None)
        return jsonify({"active": False}), 200

    if client_id and code_record["client_id"] != client_id:
        return jsonify({"active": False}), 200

    if redirect_uri and code_record["redirect_uri"] != redirect_uri:
        return jsonify({"active": False}), 200

    return jsonify(
        {
            "active": not code_record["used"],
            "user_id": code_record["user_id"],
            "client_id": code_record["client_id"],
            "redirect_uri": code_record["redirect_uri"],
            "expires_at": code_record["expires_at"],
        }
    )


@app.route("/introspect", methods=["POST"])
def introspect():
    token = request.form.get("token")
    token_record = access_tokens.get(token)

    if not token_record:
        return jsonify({"active": False})

    if time.time() > token_record["expires_at"]:
        access_tokens.pop(token, None)
        return jsonify({"active": False})

    return jsonify(
        {
            "active": True,
            "user_id": token_record["user_id"],
            "client_id": token_record["client_id"],
            "exp": int(token_record["expires_at"]),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)