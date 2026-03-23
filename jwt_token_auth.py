import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-use-a-long-random-secret")
ALGORITHM = "HS256"
DEFAULT_EXPIRES = timedelta(hours=24)


def create_access_token(
    user_id: str,
    role: str,
    *,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = DEFAULT_EXPIRES
    key = secret_key if secret_key is not None else SECRET_KEY
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, key, algorithm=ALGORITHM)


def decode_access_token(token: str, *, secret_key: str | None = None) -> dict[str, Any]:
    key = secret_key if secret_key is not None else SECRET_KEY
    return jwt.decode(token, key, algorithms=[ALGORITHM])


if __name__ == "__main__":
    token = create_access_token("user-42", "admin")
    claims = decode_access_token(token)
    assert claims["sub"] == "user-42"
    assert claims["role"] == "admin"
    print(token)
    print(claims)
