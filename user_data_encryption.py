import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.environ.get("USER_DATA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("USER_DATA_ENCRYPTION_KEY is not set")
    if isinstance(key, str):
        key = key.encode("ascii")
    return Fernet(key)


def encrypt_user_data(plaintext: str) -> str:
    """
    Encrypt UTF-8 text for database storage. Returns URL-safe base64 string.
    """
    if plaintext is None:
        raise TypeError("plaintext must not be None")
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_user_data(ciphertext: str) -> str:
    """
    Decrypt a value produced by encrypt_user_data.
    """
    if ciphertext is None:
        raise TypeError("ciphertext must not be None")
    f = _get_fernet()
    return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")


def generate_encryption_key() -> str:
    """Run once; store the returned string in USER_DATA_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode("ascii")


if __name__ == "__main__":
    os.environ["USER_DATA_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
    secret = "user@example.com"
    stored = encrypt_user_data(secret)
    assert decrypt_user_data(stored) == secret
    print("ok")
