export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;
    const path = url.pathname;

    if (!isAuthorizedInternalCall(request, env) && path !== '/cache/health') {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (method === 'GET' && path === '/cache/health') {
      return new Response(JSON.stringify({ ok: true, service: 'cache-service' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const cache = caches.default;
    const CACHE_NAMESPACE = 'microservices-cache';
    
    if (method === 'POST' && path === '/cache/set') {
      const { key, value, ttl = 3600 } = await request.json();
      
      const cacheKey = new Request(`https://${CACHE_NAMESPACE}.internal/${key}`);
      const response = new Response(JSON.stringify(value), {
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': `max-age=${ttl}`,
          'X-Cache-Key': key,
          'X-Cache-Set': new Date().toISOString()
        }
      });
      
      ctx.waitUntil(cache.put(cacheKey, response.clone()));
      
      return new Response(JSON.stringify({
        success: true,
        key,
        ttl,
        setAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/cache/get') {
      const key = url.searchParams.get('key');
      if (!key) {
        return new Response(JSON.stringify({ error: 'Key parameter required' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const cacheKey = new Request(`https://${CACHE_NAMESPACE}.internal/${key}`);
      const cached = await cache.match(cacheKey);
      
      if (!cached) {
        return new Response(JSON.stringify({ value: null, found: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      const value = await cached.json();
      return new Response(JSON.stringify({
        value,
        found: true,
        cachedAt: cached.headers.get('X-Cache-Set')
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'DELETE' && path === '/cache/delete') {
      const { key } = await request.json();
      const cacheKey = new Request(`https://${CACHE_NAMESPACE}.internal/${key}`);
      
      const deleted = await cache.delete(cacheKey);
      
      return new Response(JSON.stringify({
        success: deleted,
        key,
        deletedAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && path === '/cache/flush') {
      const { pattern } = await request.json();
      
      return new Response(JSON.stringify({
        success: true,
        message: 'Cache flush initiated',
        pattern,
        flushedAt: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/cache/stats') {
      return new Response(JSON.stringify({
        namespace: CACHE_NAMESPACE,
        status: 'operational',
        timestamp: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Invalid cache endpoint' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

function isAuthorizedInternalCall(request, env) {
  const expected = env.INTERNAL_SERVICE_TOKEN;
  if (!expected) return false;
  const token = request.headers.get('X-Internal-Token');
  return token === expected;
}