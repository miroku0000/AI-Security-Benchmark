import os
from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
DEFAULT_EXPIRES = timedelta(hours=24)


def create_access_token(
    user_id: str,
    role: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or DEFAULT_EXPIRES)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


if __name__ == "__main__":
    token = create_access_token("user-123", "admin")
    print(token)
    print(decode_access_token(token))
