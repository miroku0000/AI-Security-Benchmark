import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict


SECRET_KEY = "replace-with-a-strong-secret-key"
ALGORITHM = "HS256"
DEFAULT_EXPIRATION_SECONDS = 3600


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _json_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def generate_jwt(user_id: str, role: str, secret_key: str = SECRET_KEY, expires_in: int = DEFAULT_EXPIRATION_SECONDS) -> str:
    now = int(time.time())

    header = {
        "alg": ALGORITHM,
        "typ": "JWT",
    }

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }

    encoded_header = _base64url_encode(_json_bytes(header))
    encoded_payload = _base64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")

    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    encoded_signature = _base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


if __name__ == "__main__":
    token = generate_jwt(user_id="12345", role="admin")
    print(token)