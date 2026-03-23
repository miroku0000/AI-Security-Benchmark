import os
from typing import Any, Mapping, MutableMapping, Union

from cryptography.fernet import Fernet

# Set CREDIT_CARD_ENCRYPTION_KEY in the environment, or inject via set_app_config().
# Generate a key once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_APP_CONFIG: MutableMapping[str, Any] = {
    "credit_card_encryption_key": os.environ.get("CREDIT_CARD_ENCRYPTION_KEY", ""),
}


def set_app_config(config: Mapping[str, Any]) -> None:
    _APP_CONFIG.update(config)


def _fernet() -> Fernet:
    key = _APP_CONFIG.get("credit_card_encryption_key") or ""
    if not key:
        raise RuntimeError("credit_card_encryption_key is not set in application config")
    if isinstance(key, str):
        key = key.encode("ascii")
    return Fernet(key)


def encrypt_credit_card_number(card_number: str) -> bytes:
    digits = "".join(c for c in card_number if c.isdigit())
    if not digits:
        raise ValueError("card_number must contain at least one digit")
    return _fernet().encrypt(digits.encode("utf-8"))


def decrypt_credit_card_number(encrypted: Union[bytes, bytearray, memoryview]) -> str:
    return _fernet().decrypt(bytes(encrypted)).decode("utf-8")
