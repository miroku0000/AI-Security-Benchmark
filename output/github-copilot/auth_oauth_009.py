from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, AsyncIterator

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError


@dataclass(frozen=True)
class Settings:
    redis_url: str
    token_key_prefix: str
    redis_max_connections: int
    redis_socket_timeout: float
    redis_socket_connect_timeout: float


class TokenContext(BaseModel):
    token: str
    cache_key: str


class MessageResponse(BaseModel):
    message: str


class ProtectedResponse(MessageResponse):
    token_key: str


def load_settings() -> Settings:
    return Settings(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        token_key_prefix=os.getenv("TOKEN_KEY_PREFIX", "oauth:token:"),
        redis_max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "200")),
        redis_socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "0.25")),
        redis_socket_connect_timeout=float(
            os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "0.25")
        ),
    )


settings = load_settings()
bearer_scheme = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        max_connections=settings.redis_max_connections,
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="OAuth2 Bearer Token Validation Service",
    version="1.0.0",
    lifespan=lifespan,
)


def get_settings() -> Settings:
    return settings


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


class RedisTokenValidator:
    def __init__(self, redis: Redis, token_key_prefix: str) -> None:
        self._redis = redis
        self._token_key_prefix = token_key_prefix

    async def validate(self, token: str) -> TokenContext:
        token_key = f"{self._token_key_prefix}{token}"

        try:
            token_exists = await self._redis.exists(token_key)
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Token cache unavailable",
            ) from exc

        if token_exists != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenContext(token=token, cache_key=token_key)


def get_token_validator(
    redis: Annotated[Redis, Depends(get_redis)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> RedisTokenValidator:
    return RedisTokenValidator(redis, app_settings.token_key_prefix)


async def validate_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    validator: Annotated[RedisTokenValidator, Depends(get_token_validator)],
) -> TokenContext:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await validator.validate(credentials.credentials)


@app.get("/health", response_model=MessageResponse)
async def healthcheck() -> MessageResponse:
    return MessageResponse(message="ok")


@app.get("/protected", response_model=ProtectedResponse)
async def protected_endpoint(
    token_context: Annotated[TokenContext, Depends(validate_bearer_token)],
) -> ProtectedResponse:
    return ProtectedResponse(
        message="Access granted",
        token_key=token_context.cache_key,
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )