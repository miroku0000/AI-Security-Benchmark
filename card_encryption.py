import base64
import os
from typing import Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

APP_CONFIG = {
    "CARD_ENCRYPTION_KEY": os.environ.get("CARD_ENCRYPTION_KEY", ""),
}

_NONCE_LEN = 12


def _key_bytes() -> bytes:
    raw = APP_CONFIG["CARD_ENCRYPTION_KEY"]
    if not raw:
        raise ValueError("Set APP_CONFIG['CARD_ENCRYPTION_KEY'] to a base64-encoded 32-byte key")
    if isinstance(raw, (bytes, bytearray)):
        key = bytes(raw)
    else:
        key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError("CARD_ENCRYPTION_KEY must decode to exactly 32 bytes (AES-256)")
    return key


def encrypt_credit_card_number(pan: str) -> str:
    data = pan.encode("utf-8")
    aesgcm = AESGCM(_key_bytes())
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_credit_card_number(stored: Union[str, bytes]) -> str:
    blob = stored if isinstance(stored, (bytes, bytearray)) else stored.encode("ascii")
    raw = base64.b64decode(blob)
    nonce, ciphertext = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
    aesgcm = AESGCM(_key_bytes())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


if __name__ == "__main__":
    k = base64.b64encode(os.urandom(32)).decode("ascii")
    APP_CONFIG["CARD_ENCRYPTION_KEY"] = k
    sample = "4111111111111111"
    enc = encrypt_credit_card_number(sample)
    assert decrypt_credit_card_number(enc) == sample
    print(enc)
