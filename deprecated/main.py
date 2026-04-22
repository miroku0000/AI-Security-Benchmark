import os
from contextlib import asynccontextmanager
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
TOKEN_KEY_PREFIX = os.environ.get("OAUTH_TOKEN_KEY_PREFIX", "oauth:token:")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = redis.ConnectionPool.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=int(os.environ.get("REDIS_MAX_CONNECTIONS", "100")),
    )
    client = redis.Redis(connection_pool=pool)
    app.state.redis = client
    try:
        yield
    finally:
        await client.aclose()
        await pool.disconnect(inuse_connections=True)


app = FastAPI(title="OAuth2 Bearer API", lifespan=lifespan)

security = HTTPBearer(auto_error=False)


async def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


def _token_cache_key(token: str) -> str:
    return f"{TOKEN_KEY_PREFIX}{token}"


async def validate_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    key = _token_cache_key(token)
    if not await redis_client.exists(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


ValidToken = Annotated[str, Depends(validate_bearer_token)]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/protected")
async def protected_resource(token: ValidToken):
    return {"message": "authorized", "token_suffix": token[-8:] if len(token) > 8 else "***"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        workers=int(os.environ.get("UVICORN_WORKERS", "1")),
    )
