import os
import secrets
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from redis.cluster import RedisCluster


SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "604800"))
API_KEY_TTL_SECONDS = int(os.environ.get("API_KEY_TTL_SECONDS", "7776000"))
REDIS_USERNAME = os.environ.get("REDIS_USERNAME")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_SSL = os.environ.get("REDIS_SSL", "false").lower() in ("1", "true", "yes")
REDIS_URL = os.environ.get("REDIS_URL")
REDIS_CLUSTER_NODES = os.environ.get(
    "REDIS_CLUSTER_NODES",
    "localhost:6379",
)


def _parse_startup_nodes(spec: str) -> list[dict]:
    nodes = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            host, port_s = part.rsplit(":", 1)
            nodes.append({"host": host.strip(), "port": int(port_s.strip())})
        else:
            nodes.append({"host": part, "port": 6379})
    if not nodes:
        raise RuntimeError("REDIS_CLUSTER_NODES must define at least one host:port")
    return nodes


def create_cluster_client() -> RedisCluster:
    kwargs = {
        "decode_responses": True,
        "ssl": REDIS_SSL,
    }
    if REDIS_USERNAME:
        kwargs["username"] = REDIS_USERNAME
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    if REDIS_URL:
        return RedisCluster.from_url(REDIS_URL, **kwargs)
    return RedisCluster(startup_nodes=_parse_startup_nodes(REDIS_CLUSTER_NODES), **kwargs)


redis_client: Optional[RedisCluster] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = create_cluster_client()
    try:
        redis_client.ping()
    except Exception as e:
        redis_client.close()
        redis_client = None
        raise RuntimeError(f"Redis cluster connection failed: {e}") from e
    yield
    if redis_client is not None:
        redis_client.close()
        redis_client = None


app = FastAPI(title="cache-svc", lifespan=lifespan)


def get_redis() -> RedisCluster:
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return redis_client


class SessionCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    token: str = Field(..., min_length=8)
    ttl_seconds: Optional[int] = Field(default=None, ge=60, le=7 * 86400)


class SessionResponse(BaseModel):
    session_id: str


class ApiKeyCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=16)
    ttl_seconds: Optional[int] = Field(default=None, ge=300, le=365 * 86400)


class ApiKeyResponse(BaseModel):
    key_id: str


@app.post("/sessions", response_model=SessionResponse)
def create_session(body: SessionCreate):
    r = get_redis()
    session_id = secrets.token_urlsafe(32)
    ttl = body.ttl_seconds if body.ttl_seconds is not None else SESSION_TTL_SECONDS
    key = f"session:{session_id}"
    pipe = r.pipeline(transaction=False)
    pipe.hset(key, mapping={"user_id": body.user_id, "token": body.token})
    pipe.expire(key, ttl)
    pipe.execute()
    return SessionResponse(session_id=session_id)


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    r = get_redis()
    key = f"session:{session_id}"
    data = r.hgetall(key)
    if not data:
        raise HTTPException(status_code=404, detail="session not found")
    return {"user_id": data["user_id"], "token": data["token"]}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    r = get_redis()
    key = f"session:{session_id}"
    deleted = r.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


@app.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(body: ApiKeyCreate):
    r = get_redis()
    key_id = str(uuid.uuid4())
    ttl = body.ttl_seconds if body.ttl_seconds is not None else API_KEY_TTL_SECONDS
    key = f"apikey:{body.user_id}:{key_id}"
    pipe = r.pipeline(transaction=False)
    pipe.set(key, body.api_key, ex=ttl)
    pipe.execute()
    return ApiKeyResponse(key_id=key_id)


@app.get("/api-keys/{user_id}/{key_id}")
def get_api_key(user_id: str, key_id: str):
    r = get_redis()
    key = f"apikey:{user_id}:{key_id}"
    value = r.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="api key not found")
    return {"api_key": value}


@app.delete("/api-keys/{user_id}/{key_id}")
def delete_api_key(user_id: str, key_id: str):
    r = get_redis()
    key = f"apikey:{user_id}:{key_id}"
    deleted = r.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="api key not found")
    return {"ok": True}


@app.get("/health")
def health():
    r = get_redis()
    r.ping()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "redis_cache_service:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        workers=int(os.environ.get("UVICORN_WORKERS", "1")),
    )
