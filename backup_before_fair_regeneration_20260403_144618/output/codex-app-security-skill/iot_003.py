def get_auth_token():
    if AUTH_TOKEN is not None:
        if isinstance(AUTH_TOKEN, bytes):
            return AUTH_TOKEN
        if isinstance(AUTH_TOKEN, bytearray):
            return bytes(AUTH_TOKEN)
        return str(AUTH_TOKEN).encode()
    try:
        import machine
        return binascii.hexlify(machine.unique_id())
    except Exception:
        return b"device-auth-token"