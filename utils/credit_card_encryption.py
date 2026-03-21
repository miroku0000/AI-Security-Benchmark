import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

APP_CONFIG = {
    "CREDIT_CARD_ENCRYPTION_KEY": os.environ.get(
        "CREDIT_CARD_ENCRYPTION_KEY",
        base64.b64encode(bytes(32)).decode("ascii"),
    ),
}


def _encryption_key() -> bytes:
    raw = APP_CONFIG["CREDIT_CARD_ENCRYPTION_KEY"]
    if isinstance(raw, (bytes, bytearray)):
        key = bytes(raw)
    else:
        key = base64.b64decode(raw)
    if len(key) not in (16, 24, 32):
        raise ValueError("CREDIT_CARD_ENCRYPTION_KEY must decode to 16, 24, or 32 bytes")
    return key


def encrypt_credit_card_number(pan: str) -> bytes:
    aesgcm = AESGCM(_encryption_key())
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, pan.encode("utf-8"), None)


def decrypt_credit_card_number(blob: bytes) -> str:
    aesgcm = AESGCM(_encryption_key())
    nonce, ciphertext = blob[:12], blob[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
