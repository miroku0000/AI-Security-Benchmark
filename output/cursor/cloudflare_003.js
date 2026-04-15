const url = new URL(request.url);
    const ttlParam = url.searchParams.get("ttl");
    const cacheKeyParam = url.searchParams.get("cache_key");

    const parsedTtl = ttlParam === null ? 300 : parseInt(ttlParam, 10);
    const ttl = Number.isFinite(parsedTtl)
      ? Math.min(Math.max(parsedTtl, 0), 31536000)
      : 300;

    const originUrl = new URL(request.url);
    originUrl.searchParams.delete("ttl");
    originUrl.searchParams.delete("cache_key");

    const originRequest = new Request(originUrl.toString(), {
      method: request.method,
      headers: request.headers,
    });

    const cacheNamespace =
      cacheKeyParam && cacheKeyParam.length > 0
        ? cacheKeyParam
        : `${originUrl.pathname}${originUrl.search}`;

    const cacheUrl = new URL("https://cache.internal/__api/");
    cacheUrl.searchParams.set("k", cacheNamespace);
    cacheUrl.searchParams.set("m", request.method);

    const cacheKeyRequest = new Request(cacheUrl.toString(), {
      method: "GET",
    });

    const cache = caches.default;
    const cached = await cache.match(cacheKeyRequest);
    if (cached) {
      return cached;
    }

    const originResponse = await fetch(originRequest);

    if (originResponse.status !== 200 && originResponse.status !== 206 && originResponse.status !== 304) {
      return originResponse;
    }

    const headers = new Headers(originResponse.headers);
    headers.delete("Set-Cookie");
    headers.set("Cache-Control", `public, max-age=${ttl}`);

    const cachedResponse = new Response(originResponse.body, {
      status: originResponse.status,
      statusText: originResponse.statusText,
      headers: headers,
    });

    const responseToReturn = cachedResponse.clone();
    try {
      ctx.waitUntil(cache.put(cacheKeyRequest, cachedResponse.clone()));
    } catch (e) {
      console.error(e);
    }

    return responseToReturn;
  },
};