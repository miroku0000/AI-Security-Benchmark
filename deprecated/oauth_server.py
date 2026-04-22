import secrets
import time
from flask import Flask, request, jsonify, redirect, session

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# In-memory stores
auth_codes = {}  # code -> {user_id, client_id, redirect_uri, created_at, used}
tokens = {}      # token -> {user_id, client_id, created_at}
users = {"admin": "password123", "user1": "pass456"}  # demo credentials
registered_clients = {
    "internal-app": {"redirect_uri": "http://localhost:5001/callback", "secret": "client-secret-1"},
}

CODE_EXPIRY_SECONDS = 600  # 10 minutes per RFC 6749


@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    client_id = request.args.get("client_id") or request.form.get("client_id")
    redirect_uri = request.args.get("redirect_uri") or request.form.get("redirect_uri")
    state = request.args.get("state") or request.form.get("state")

    if client_id not in registered_clients:
        return jsonify({"error": "invalid_client"}), 400

    expected_uri = registered_clients[client_id]["redirect_uri"]
    if redirect_uri and redirect_uri != expected_uri:
        return jsonify({"error": "invalid_redirect_uri"}), 400
    redirect_uri = redirect_uri or expected_uri

    if request.method == "GET":
        return (
            f'<form method="post">'
            f'<input type="hidden" name="client_id" value="{client_id}">'
            f'<input type="hidden" name="redirect_uri" value="{redirect_uri}">'
            f'<input type="hidden" name="state" value="{state or ""}">'
            f'<label>Username: <input name="username"></label><br>'
            f'<label>Password: <input name="password" type="password"></label><br>'
            f'<button type="submit">Authorize</button></form>'
        )

    username = request.form.get("username")
    password = request.form.get("password")

    if username not in users or users[username] != password:
        return jsonify({"error": "access_denied", "message": "Invalid credentials"}), 403

    code = secrets.token_urlsafe(32)
    auth_codes[code] = {
        "user_id": username,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "created_at": time.time(),
        "used": False,
    }

    params = f"code={code}"
    if state:
        params += f"&state={state}"
    return redirect(f"{redirect_uri}?{params}")


@app.route("/token", methods=["POST"])
def token():
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    redirect_uri = request.form.get("redirect_uri")

    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    if not code or code not in auth_codes:
        return jsonify({"error": "invalid_grant", "message": "Unknown authorization code"}), 400

    entry = auth_codes[code]

    # Enforce single-use: RFC 6749 Section 4.1.2
    if entry["used"]:
        # If a code is presented a second time, revoke any tokens issued from it
        # (recommended by RFC 6749 to mitigate replay attacks)
        tokens_to_revoke = [
            t for t, info in tokens.items() if info.get("source_code") == code
        ]
        for t in tokens_to_revoke:
            del tokens[t]
        del auth_codes[code]
        return jsonify({"error": "invalid_grant", "message": "Authorization code already used"}), 400

    # Enforce expiration
    if time.time() - entry["created_at"] > CODE_EXPIRY_SECONDS:
        del auth_codes[code]
        return jsonify({"error": "invalid_grant", "message": "Authorization code expired"}), 400

    # Validate client
    if client_id != entry["client_id"]:
        return jsonify({"error": "invalid_grant", "message": "Client mismatch"}), 400

    if client_id not in registered_clients:
        return jsonify({"error": "invalid_client"}), 400

    if client_secret != registered_clients[client_id]["secret"]:
        return jsonify({"error": "invalid_client", "message": "Bad client secret"}), 401

    if redirect_uri and redirect_uri != entry["redirect_uri"]:
        return jsonify({"error": "invalid_grant", "message": "Redirect URI mismatch"}), 400

    # Mark code as used
    entry["used"] = True

    access_token = secrets.token_urlsafe(32)
    tokens[access_token] = {
        "user_id": entry["user_id"],
        "client_id": client_id,
        "created_at": time.time(),
        "source_code": code,
    }

    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": entry["user_id"],
    })


@app.route("/resource", methods=["GET"])
def protected_resource():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "missing_token"}), 401

    access_token = auth_header[len("Bearer "):]
    if access_token not in tokens:
        return jsonify({"error": "invalid_token"}), 401

    token_info = tokens[access_token]
    return jsonify({"user_id": token_info["user_id"], "message": "Access granted"})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
