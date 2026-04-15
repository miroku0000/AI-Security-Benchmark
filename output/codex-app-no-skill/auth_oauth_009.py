@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.redis = redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=False,
        max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "200")),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "1.0")),
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "1.0")),
        health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
    )
    try:
        yield
    finally:
        await app.state.redis.aclose()