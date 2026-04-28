import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class AppConfig:
    credit_card_key_b64: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        key_b64 = os.environ["CREDIT_CARD_KEY_B64"]
        return cls(credit_card_key_b64=key_b64)

    def get_credit_card_key(self) -> bytes:
        key = base64.b64decode(self.credit_card_key_b64)
        if len(key) not in (16, 24, 32):
            raise ValueError("CREDIT_CARD_KEY_B64 must decode to 16, 24, or 32 bytes")
        return key


class CreditCardEncryptor:
    def __init__(self, config: AppConfig):
        self._aesgcm = AESGCM(config.get_credit_card_key())

    def encrypt_card_number(self, card_number: str) -> str:
        plaintext = card_number.strip().encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt_card_number(self, encrypted_value: str) -> str:
        data = base64.b64decode(encrypted_value)
        nonce, ciphertext = data[:12], data[12:]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")


def build_credit_card_encryptor() -> CreditCardEncryptor:
    return CreditCardEncryptor(AppConfig.from_env())


if __name__ == "__main__":
    if "CREDIT_CARD_KEY_B64" not in os.environ:
        os.environ["CREDIT_CARD_KEY_B64"] = base64.b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")

    encryptor = build_credit_card_encryptor()
    card_number = "4111111111111111"
    encrypted = encryptor.encrypt_card_number(card_number)
    decrypted = encryptor.decrypt_card_number(encrypted)

    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")