def generate_access_token(user_id: str, role: str) -> str:
    now = _utc_now()
    payload = {
        "sub": _normalize_user_id(user_id),
        "role": _validate_role(role),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_LIFETIME_MINUTES)).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        _get_signing_key(),
        algorithm=JWT_ALGORITHM,
        headers={"typ": "JWT"},
    )