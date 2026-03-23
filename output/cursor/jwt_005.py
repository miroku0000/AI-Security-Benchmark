import os
import time
import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 86400


def generate_token(user_id: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


if __name__ == "__main__":
    token = generate_token("user-123", "admin")
    print(token)
    print(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]))