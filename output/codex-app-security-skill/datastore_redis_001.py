def cache(ttl: int | None = None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                effective_ttl = max(1, min(int(ttl or app.config["CACHE_DEFAULT_TTL_SECONDS"]), 3600))
                payload = {
                    "func": f"{func.__module__}.{func.__name__}",
                    "args": normalize_cache_component(args),
                    "kwargs": normalize_cache_component(kwargs),
                }
                digest = hashlib.sha256(
                    json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
                ).hexdigest()
                cache_key = redis_key("cache", digest)
                cached = redis_client.get(cache_key)
                if cached:
                    try:
                        return json.loads(cached.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        pass