class CardEncryptionService:
    def __init__(self, config: AppConfig):
        key = base64.b64decode(config.card_encryption_key_b64)
        if len(key) not in (16, 24, 32):
            raise ValueError("CARD_ENCRYPTION_KEY_B64 must decode to a 16, 24, or 32 byte key")
        self._aesgcm = AESGCM(key)