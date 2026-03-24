def encrypt_card_number(card_number: str, record_context: Optional[str] = None) -> str:
    pan = _normalize_pan(card_number)
    key = _load_key_from_env()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, pan.encode("utf-8"), _build_aad(record_context))
    return f"{KEY_VERSION}.{_b64url_encode(nonce)}.{_b64url_encode(ciphertext)}"