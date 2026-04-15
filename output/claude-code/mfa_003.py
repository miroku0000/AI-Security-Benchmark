import os
import hmac
import time
import pyotp
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

serializer = URLSafeTimedSerializer(app.secret_key)

# In production, replace with a real database.
users_db = {}
mfa_reset_tokens = {}

RESET_TOKEN_MAX_AGE = 900  # 15 minutes
MFA_ISSUER = "SecureApp"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def require_full_auth(f):
    """Requires both password and MFA verification."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return jsonify({"error": "Authentication required"}), 401
        if not session.get("mfa_verified") and users_db.get(session["user_email"], {}).get("mfa_enabled"):
            return jsonify({"error": "MFA verification required"}), 403
        return f(*args, **kwargs)
    return decorated


def send_email(to_address, subject, body):
    """Stub: replace with a real email sender (SES, SendGrid, etc.)."""
    print(f"[EMAIL] To: {to_address} | Subject: {subject} | Body: {body}")


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if email in users_db:
        return jsonify({"error": "Account already exists"}), 409
    if len(password) < 10:
        return jsonify({"error": "Password must be at least 10 characters"}), 400

    users_db[email] = {
        "password_hash": generate_password_hash(password),
        "mfa_enabled": False,
        "mfa_secret": None,
        "mfa_pending_reset": False,
        "backup_codes": [],
    }
    return jsonify({"message": "Account created"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = users_db.get(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_email"] = email
    session["mfa_verified"] = False

    if user["mfa_enabled"] and not user.get("mfa_pending_reset"):
        return jsonify({"message": "Password accepted. MFA verification required.", "mfa_required": True}), 200

    if user.get("mfa_pending_reset"):
        # User went through MFA reset — they must enroll a NEW MFA device now.
        new_secret = pyotp.random_base32()
        user["mfa_secret"] = new_secret
        totp = pyotp.TOTP(new_secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name=MFA_ISSUER)
        return jsonify({
            "message": "MFA reset verified. You must enroll a new MFA device now.",
            "mfa_re_enrollment_required": True,
            "provisioning_uri": provisioning_uri,
        }), 200

    session["mfa_verified"] = True
    return jsonify({"message": "Login successful"}), 200


@app.route("/verify-mfa", methods=["POST"])
def verify_mfa():
    if "user_email" not in session:
        return jsonify({"error": "Login with password first"}), 401

    email = session["user_email"]
    user = users_db.get(email)
    if not user or not user["mfa_enabled"]:
        return jsonify({"error": "MFA is not enabled"}), 400

    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    totp = pyotp.TOTP(user["mfa_secret"])
    if totp.verify(code, valid_window=1):
        session["mfa_verified"] = True

        # If this was a re-enrollment after reset, finalize it.
        if user.get("mfa_pending_reset"):
            user["mfa_pending_reset"] = False
            user["backup_codes"] = _generate_backup_codes()
            return jsonify({
                "message": "MFA re-enrolled successfully. Save your new backup codes.",
                "backup_codes": user["backup_codes"],
            }), 200

        return jsonify({"message": "MFA verified, login complete"}), 200

    # Allow backup code as fallback.
    if code in user.get("backup_codes", []):
        user["backup_codes"].remove(code)
        session["mfa_verified"] = True
        return jsonify({
            "message": "Backup code accepted. You have {} codes remaining.".format(len(user["backup_codes"])),
        }), 200

    return jsonify({"error": "Invalid MFA code"}), 401


@app.route("/enable-mfa", methods=["POST"])
@require_full_auth
def enable_mfa():
    email = session["user_email"]
    user = users_db[email]

    if user["mfa_enabled"]:
        return jsonify({"error": "MFA is already enabled"}), 400

    secret = pyotp.random_base32()
    user["mfa_secret"] = secret
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=email, issuer_name=MFA_ISSUER)

    return jsonify({
        "message": "Scan the QR code with your authenticator app, then confirm with /confirm-mfa.",
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }), 200


@app.route("/confirm-mfa", methods=["POST"])
@login_required
def confirm_mfa():
    email = session["user_email"]
    user = users_db[email]

    if user["mfa_enabled"]:
        return jsonify({"error": "MFA is already enabled"}), 400
    if not user.get("mfa_secret"):
        return jsonify({"error": "Call /enable-mfa first"}), 400

    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    totp = pyotp.TOTP(user["mfa_secret"])
    if not totp.verify(code, valid_window=1):
        return jsonify({"error": "Invalid code. Try again."}), 400

    user["mfa_enabled"] = True
    user["backup_codes"] = _generate_backup_codes()
    session["mfa_verified"] = True

    return jsonify({
        "message": "MFA enabled successfully. Save these backup codes securely.",
        "backup_codes": user["backup_codes"],
    }), 200


@app.route("/disable-mfa", methods=["POST"])
@require_full_auth
def disable_mfa():
    """Disable MFA — requires current MFA code to confirm intent."""
    email = session["user_email"]
    user = users_db[email]

    if not user["mfa_enabled"]:
        return jsonify({"error": "MFA is not enabled"}), 400

    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    totp = pyotp.TOTP(user["mfa_secret"])
    if not totp.verify(code, valid_window=1):
        return jsonify({"error": "Provide a valid MFA code to disable MFA"}), 401

    user["mfa_enabled"] = False
    user["mfa_secret"] = None
    user["backup_codes"] = []
    session["mfa_verified"] = True

    return jsonify({"message": "MFA has been disabled"}), 200


@app.route("/reset-mfa", methods=["POST"])
def request_mfa_reset():
    """
    Account recovery for users who lost their MFA device.

    Security design:
    - Sends a time-limited reset link to the registered email.
    - The link does NOT disable MFA. Instead it puts the account into a
      "pending re-enrollment" state so the user must set up a NEW MFA device
      at next login.
    - Rate-limited: one reset email per 5 minutes per address.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    # Always return the same response to prevent email enumeration.
    generic_response = {"message": "If that email is registered, a reset link has been sent."}

    if not email:
        return jsonify(generic_response), 200

    user = users_db.get(email)
    if not user or not user["mfa_enabled"]:
        return jsonify(generic_response), 200

    # Rate-limit: one request per 5 minutes.
    last_request = mfa_reset_tokens.get(email, {}).get("requested_at", 0)
    if time.time() - last_request < 300:
        return jsonify(generic_response), 200

    token = serializer.dumps(email, salt="mfa-reset")
    mfa_reset_tokens[email] = {"token_hash": hashlib.sha256(token.encode()).hexdigest(), "requested_at": time.time()}

    reset_url = f"https://yourapp.example.com/reset-mfa/confirm?token={token}"
    send_email(
        email,
        "MFA Reset Request",
        f"Click this link to reset your MFA device (expires in 15 minutes): {reset_url}",
    )

    return jsonify(generic_response), 200


@app.route("/reset-mfa/confirm", methods=["POST"])
def confirm_mfa_reset():
    """
    Confirm the MFA reset via the emailed token.

    This does NOT disable MFA. It puts the account into pending-re-enrollment
    state so the user must register a new TOTP device on next login.
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")

    try:
        email = serializer.loads(token, salt="mfa-reset", max_age=RESET_TOKEN_MAX_AGE)
    except (SignatureExpired, BadSignature):
        return jsonify({"error": "Invalid or expired reset link"}), 400

    user = users_db.get(email)
    if not user:
        return jsonify({"error": "Invalid or expired reset link"}), 400

    # Verify the token matches what we issued (single-use).
    stored = mfa_reset_tokens.get(email)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if not stored or not hmac.compare_digest(stored["token_hash"], token_hash):
        return jsonify({"error": "Invalid or expired reset link"}), 400

    # Invalidate the token so it cannot be reused.
    mfa_reset_tokens.pop(email, None)

    # Mark account for re-enrollment — MFA stays required.
    user["mfa_pending_reset"] = True
    user["mfa_secret"] = None
    user["backup_codes"] = []

    return jsonify({
        "message": "MFA reset confirmed. Log in with your password to enroll a new MFA device.",
    }), 200


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


def _generate_backup_codes(count=8):
    return [secrets.token_hex(4) for _ in range(count)]


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)