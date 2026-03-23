import os
from typing import Union

from cryptography.fernet import Fernet


def encrypt_user_data(plaintext: Union[str, bytes], key: Union[bytes, str, None] = None) -> bytes:
    if key is None:
        raw = os.environ.get("ENCRYPTION_KEY")
        if not raw:
            raise ValueError("ENCRYPTION_KEY must be set to a Fernet key")
        key = raw.encode("ascii") if isinstance(raw, str) else raw
    elif isinstance(key, str):
        key = key.encode("ascii")
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    return Fernet(key).encrypt(plaintext)


if __name__ == "__main__":
    _k = Fernet.generate_key()
    os.environ["ENCRYPTION_KEY"] = _k.decode("ascii")
    print(encrypt_user_data("sensitive value"))
