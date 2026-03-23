def _get_key(config: Optional[Mapping[str, str]] = None) -> bytes:
    source = config if config is not None else APP_CONFIG
    encoded_key = source.get("CC_ENCRYPTION_KEY", "")
    if not encoded_key:
        raise ValueError("Missing CC_ENCRYPTION_KEY in application config")
    try:
        key = base64.b64decode(encoded_key)
    except Exception as exc:
        raise ValueError("CC_ENCRYPTION_KEY must be valid base64") from exc
    if len(key) != 32:
        raise ValueError("CC_ENCRYPTION_KEY must decode to 32 bytes for AES-256")
    return key