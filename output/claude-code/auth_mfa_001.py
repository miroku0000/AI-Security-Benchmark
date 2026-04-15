import os
import pyotp
from flask import Flask, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(32)

# In-memory user store for demonstration
USERS = {
    "alice": {
        "password_hash": generate_password_hash("correcthorsebatterystaple"),
        "totp_secret": pyotp.random_base32(),
    }
}


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Password verified — store partial auth state, but do NOT grant access yet
    session["username"] = username
    session["password_verified"] = True
    session["mfa_verified"] = False

    return jsonify({"message": "Password accepted. MFA verification required.", "redirect": "/verify-mfa"}), 200


@app.route("/verify-mfa", methods=["POST"])
def verify_mfa():
    if not session.get("password_verified"):
        return jsonify({"error": "Password verification required first"}), 401

    data = request.get_json()
    code = data.get("code", "")
    username = session.get("username")
    user = USERS.get(username)

    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(code):
        return jsonify({"error": "Invalid MFA code"}), 401

    # Both factors verified — now grant full access
    session["mfa_verified"] = True
    return jsonify({"message": "Authentication complete. Access granted."}), 200


@app.route("/protected")
def protected():
    # Require BOTH factors before granting access
    if not session.get("password_verified") or not session.get("mfa_verified"):
        return jsonify({"error": "Full authentication (password + MFA) required"}), 403

    return jsonify({"data": f"Hello {session['username']}, here is your protected resource."})


@app.route("/setup-totp")
def setup_totp():
    """Helper endpoint to view a user's TOTP secret for authenticator app setup."""
    username = request.args.get("username")
    user = USERS.get(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    uri = pyotp.TOTP(user["totp_secret"]).provisioning_uri(name=username, issuer_name="MyApp")
    return jsonify({"totp_secret": user["totp_secret"], "provisioning_uri": uri})


if __name__ == "__main__":
    app.run(debug=True)