import json
import os

from cryptography.fernet import Fernet


def encrypt_sensitive_user_data(data: dict) -> str:
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    key = os.environ.get("DATA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("DATA_ENCRYPTION_KEY environment variable is required")

    try:
        fernet = Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError("DATA_ENCRYPTION_KEY is invalid") from exc

    plaintext = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return fernet.encrypt(plaintext).decode("utf-8")


if __name__ == "__main__":
    sample_data = {
        "user_id": 123,
        "email": "user@example.com",
        "ssn": "123-45-6789",
    }
    print(encrypt_sensitive_user_data(sample_data))