import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_fernet(secret: bytes | None = None, salt: bytes | None = None) -> Fernet:
    key_material = secret or os.environ.get("USER_DATA_ENCRYPTION_KEY", "").encode()
    if not key_material:
        raise ValueError("Set USER_DATA_ENCRYPTION_KEY or pass secret=")
    salt = salt or os.environ.get("USER_DATA_ENCRYPTION_SALT", "app-user-data-salt").encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_material))
    return Fernet(key)


def encrypt_user_data(plaintext: str | bytes, secret: bytes | None = None, salt: bytes | None = None) -> bytes:
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    f = _get_fernet(secret=secret, salt=salt)
    return f.encrypt(plaintext)


def decrypt_user_data(ciphertext: bytes, secret: bytes | None = None, salt: bytes | None = None) -> str:
    f = _get_fernet(secret=secret, salt=salt)
    return f.decrypt(ciphertext).decode("utf-8")


if __name__ == "__main__":
    os.environ["USER_DATA_ENCRYPTION_KEY"] = "change-this-to-a-long-random-secret"
    blob = encrypt_user_data("credit-card-4242")
    assert decrypt_user_data(blob) == "credit-card-4242"
    print("ok")