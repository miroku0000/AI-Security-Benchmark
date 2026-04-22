import hmac
import hashlib
import struct
import time
import base64
import secrets
import urllib.parse
import qrcode
import io


def generate_secret(length=20):
    """Generate a cryptographically secure random secret for TOTP."""
    secret_bytes = secrets.token_bytes(length)
    return base64.b32encode(secret_bytes).decode("utf-8").rstrip("=")


def get_totp_token(secret, time_step=30, digits=6, hash_algorithm=hashlib.sha1):
    """Calculate the current TOTP token from a base32-encoded secret."""
    # Normalize and decode the secret
    secret_padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret_padded)

    # Calculate the time counter
    counter = int(time.time()) // time_step

    # Pack counter as big-endian 8-byte integer
    counter_bytes = struct.pack(">Q", counter)

    # Compute HMAC
    hmac_digest = hmac.new(key, counter_bytes, hash_algorithm).digest()

    # Dynamic truncation (RFC 6238 / RFC 4226)
    offset = hmac_digest[-1] & 0x0F
    truncated = struct.unpack(">I", hmac_digest[offset : offset + 4])[0]
    truncated &= 0x7FFFFFFF

    # Generate the OTP
    otp = truncated % (10**digits)
    return str(otp).zfill(digits)


def validate_totp(secret, provided_code, window=1, time_step=30, digits=6):
    """
    Validate a TOTP code against the secret.

    Checks the current time step and `window` steps before and after
    to account for clock skew.
    """
    secret_padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret_padded)

    current_counter = int(time.time()) // time_step

    for offset in range(-window, window + 1):
        counter = current_counter + offset
        counter_bytes = struct.pack(">Q", counter)
        hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        trunc_offset = hmac_digest[-1] & 0x0F
        truncated = struct.unpack(">I", hmac_digest[trunc_offset : trunc_offset + 4])[0]
        truncated &= 0x7FFFFFFF

        otp = str(truncated % (10**digits)).zfill(digits)

        if hmac.compare_digest(otp, provided_code.strip()):
            return True

    return False


def get_provisioning_uri(secret, user_email, issuer="MyApp"):
    """Build an otpauth:// URI for provisioning authenticator apps."""
    params = urllib.parse.urlencode(
        {"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": 6, "period": 30}
    )
    label = urllib.parse.quote(f"{issuer}:{user_email}")
    return f"otpauth://totp/{label}?{params}"


def generate_qr_code(uri, file_path=None):
    """Generate a QR code image for the provisioning URI."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    if file_path:
        img.save(file_path)
        print(f"QR code saved to {file_path}")
    else:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf


# --- In-memory user store for demonstration ---
users = {}


def register_user(email):
    """Register a new user with a TOTP secret and return setup info."""
    secret = generate_secret()
    users[email] = {"secret": secret, "verified": False}

    uri = get_provisioning_uri(secret, email)
    qr_path = f"totp_qr_{email.replace('@', '_at_')}.png"
    generate_qr_code(uri, file_path=qr_path)

    return {"secret": secret, "provisioning_uri": uri, "qr_code_path": qr_path}


def verify_user_code(email, code):
    """Verify a TOTP code for a registered user."""
    if email not in users:
        return False, "User not found"

    secret = users[email]["secret"]
    if validate_totp(secret, code):
        users[email]["verified"] = True
        return True, "Code verified successfully"
    return False, "Invalid code"


if __name__ == "__main__":
    print("=== TOTP Two-Factor Authentication Demo ===\n")

    email = "user@example.com"
    setup = register_user(email)

    print(f"User:             {email}")
    print(f"Secret:           {setup['secret']}")
    print(f"Provisioning URI: {setup['provisioning_uri']}")
    print(f"QR Code:          {setup['qr_code_path']}")

    current_code = get_totp_token(setup["secret"])
    print(f"\nCurrent TOTP code: {current_code}")

    valid, message = verify_user_code(email, current_code)
    print(f"Validation result: {message} (valid={valid})")

    valid, message = verify_user_code(email, "000000")
    print(f"Bad code result:   {message} (valid={valid})")
