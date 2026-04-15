const url = new URL(request.url);
    const ttl = parseTtl(url.searchParams.get("ttl"));
    const customKey = url.searchParams.get("cache_key");
    const originRequest = buildOriginRequest(request);
    const cacheRequest = buildCacheRequest(request, originRequest, customKey);
    const cache = caches.default;