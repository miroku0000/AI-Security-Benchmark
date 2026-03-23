if (expSec && expSec > nowSec) {
      const tokenRemainingMs = (expSec - nowSec) * 1000;
      const cacheTtlMs = Math.min(tokenRemainingMs, Number(JWT_CACHE_TTL_MS) || 0);
      if (cacheTtlMs > 0) {
        const originalTtl = verifiedTokenCache.ttlMs;
        verifiedTokenCache.ttlMs = cacheTtlMs;
        verifiedTokenCache.set(token, auth);
        verifiedTokenCache.ttlMs = originalTtl;
      }
    }