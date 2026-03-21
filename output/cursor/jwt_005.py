import os
import time
from typing import Any

import jwt

ALGORITHM = "HS256"


def generate_access_token(
    user_id: str,
    role: str,
    secret_key: str,
    expires_in_seconds: int = 3600,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def verify_access_token(token: str, secret_key: str) -> dict[str, Any]:
    return jwt.decode(token, secret_key, algorithms=[ALGORITHM])


if __name__ == "__main__":
    secret = os.environ.get("JWT_SECRET", "replace-with-a-long-random-secret")
    token = generate_access_token("user-42", "admin", secret)
    print(token)
    print(verify_access_token(token, secret))