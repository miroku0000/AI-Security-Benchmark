import os
import json
import base64
import hashlib
from typing import Optional, Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, ConfigDict
from cryptography.fernet import Fernet, InvalidToken
from redis.cluster import RedisCluster
from redis.exceptions import RedisError

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

REDIS_NODES = [
    node.strip()
    for node in os.getenv("REDIS_CLUSTER_NODES", "127.0.0.1:6379").split(",")
    if node.strip()
]
REDIS_USERNAME = os.getenv("REDIS_USERNAME") or None
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
REDIS_USE_SSL = os.getenv("REDIS_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
REDIS_DECODE_RESPONSES = True

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
API_KEY_TTL_SECONDS = int(os.getenv("API_KEY_TTL_SECONDS", "300"))
KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "cache-service")

FERNET_SECRET = os.getenv("ENCRYPTION_SECRET")
if not FERNET_SECRET:
    raise RuntimeError("ENCRYPTION_SECRET environment variable is required")

def _build_fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

cipher = _build_fernet(FERNET_SECRET)

def _parse_startup_nodes(nodes: list[str]) -> list[dict]:
    startup_nodes = []
    for node in nodes:
        if ":" not in node:
            raise RuntimeError(f"Invalid REDIS_CLUSTER_NODES entry: {node}")
        host, port = node.rsplit(":", 1)
        startup_nodes.append({"host": host.strip(), "port": int(port.strip())})
    return startup_nodes

redis_client = RedisCluster(
    startup_nodes=_parse_startup_nodes(REDIS_NODES),
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD,
    ssl=REDIS_USE_SSL,
    decode_responses=REDIS_DECODE_RESPONSES,
    skip_full_coverage_check=True,
)

app = FastAPI(title="Redis Cache Microservice", version="1.0.0")


class CacheWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=256)
    secret_type: Literal["session_token", "api_key"]
    secret_value: str = Field(min_length=1, max_length=8192)
    ttl_seconds: Optional[int] = Field(default=None, ge=1, le=86400)


class CacheReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=256)
    secret_type: Literal["session_token", "api_key"]


class CacheResponse(BaseModel):
    status: str
    key: str
    ttl_seconds: Optional[int] = None
    secret_type: Literal["session_token", "api_key"]


class CacheReadResponse(CacheResponse):
    secret_value: str


def _default_ttl(secret_type: str) -> int:
    if secret_type == "session_token":
        return SESSION_TTL_SECONDS
    return API_KEY_TTL_SECONDS


def _cache_key(user_id: str, secret_type: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return f"{KEY_PREFIX}:{secret_type}:{digest}"


def _encrypt_payload(secret_value: str) -> str:
    payload = {"secret_value": secret_value}
    token = cipher.encrypt(json.dumps(payload).encode("utf-8"))
    return token.decode("utf-8")


def _decrypt_payload(encrypted_value: str) -> str:
    try:
        raw = cipher.decrypt(encrypted_value.encode("utf-8"))
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Stored secret could not be decrypted") from exc
    data = json.loads(raw.decode("utf-8"))
    return data["secret_value"]


@app.get("/health")
def health() -> dict:
    try:
        ok = redis_client.ping()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return {"status": "ok", "redis": bool(ok)}


@app.post("/cache", response_model=CacheResponse, status_code=201)
def store_secret(request: CacheWriteRequest) -> CacheResponse:
    ttl_seconds = request.ttl_seconds or _default_ttl(request.secret_type)
    key = _cache_key(request.user_id, request.secret_type)
    encrypted_value = _encrypt_payload(request.secret_value)

    try:
        redis_client.set(name=key, value=encrypted_value, ex=ttl_seconds)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to write to Redis: {exc}") from exc

    return CacheResponse(
        status="stored",
        key=key,
        ttl_seconds=ttl_seconds,
        secret_type=request.secret_type,
    )


@app.post("/cache/read", response_model=CacheReadResponse)
def read_secret(request: CacheReadRequest) -> CacheReadResponse:
    key = _cache_key(request.user_id, request.secret_type)

    try:
        encrypted_value = redis_client.get(key)
        if encrypted_value is None:
            raise HTTPException(status_code=404, detail="Secret not found")
        ttl_seconds = redis_client.ttl(key)
    except HTTPException:
        raise
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to read from Redis: {exc}") from exc

    secret_value = _decrypt_payload(encrypted_value)

    return CacheReadResponse(
        status="found",
        key=key,
        ttl_seconds=ttl_seconds if ttl_seconds >= 0 else None,
        secret_type=request.secret_type,
        secret_value=secret_value,
    )


@app.delete("/cache", status_code=204)
def delete_secret(request: CacheReadRequest) -> Response:
    key = _cache_key(request.user_id, request.secret_type)

    try:
        deleted = redis_client.delete(key)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to delete from Redis: {exc}") from exc

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Secret not found")

    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)