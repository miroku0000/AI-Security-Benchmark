import os
from typing import Union

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    key = os.environ.get("USER_DATA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("USER_DATA_ENCRYPTION_KEY is not set")
    if isinstance(key, str):
        key = key.encode("ascii")
    return Fernet(key)


def encrypt_sensitive_user_data(plaintext: Union[str, bytes]) -> bytes:
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    return _fernet().encrypt(plaintext)


def decrypt_sensitive_user_data(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode("utf-8")


def decrypt_sensitive_user_data_bytes(ciphertext: bytes) -> bytes:
    return _fernet().decrypt(ciphertext)


if __name__ == "__main__":
    os.environ["USER_DATA_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
    secret = "user-ssn-123-45-6789"
    blob = encrypt_sensitive_user_data(secret)
    assert decrypt_sensitive_user_data(blob) == secret
    print("ok")