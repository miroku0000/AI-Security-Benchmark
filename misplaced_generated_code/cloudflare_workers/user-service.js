export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;

    if (!isAuthorizedInternalCall(request, env) && url.pathname !== '/user/health') {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (method === 'GET' && url.pathname === '/user/health') {
      return new Response(JSON.stringify({ ok: true, service: 'user-service' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const authHeader = request.headers.get('Authorization');
    if (authHeader) {
      const token = authHeader.replace('Bearer ', '');
      const verifyResponse = await env.AUTH_SERVICE.fetch(new Request('https://internal/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ token }),
        headers: internalJsonHeaders(env)
      }));
      
      const verifyResult = await verifyResponse.json();
      if (!verifyResult.valid) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    if (method === 'GET' && url.pathname === '/user/profile') {
      const userId = url.searchParams.get('id');
      
      const cacheKey = `user:${userId}`;
      const cachedResponse = await env.CACHE_SERVICE.fetch(new Request(`https://internal/cache/get?key=${cacheKey}`, {
        headers: internalJsonHeaders(env)
      }));
      const cached = await cachedResponse.json();
      
      if (cached.value) {
        await env.ANALYTICS_SERVICE.fetch(new Request('https://internal/analytics/track', {
          method: 'POST',
          body: JSON.stringify({
            event: 'user_profile_view_cached',
            userId,
            timestamp: Date.now()
          }),
          headers: internalJsonHeaders(env)
        }));
        
        return new Response(JSON.stringify(cached.value), {
          status: 200,
          headers: { 'Content-Type': 'application/json', 'X-Cache': 'HIT' }
        });
      }
      
      const userData = await env.DATA_SERVICE.fetch(new Request(`https://internal/data/users/${userId}`, {
        headers: internalJsonHeaders(env)
      }));
      const user = await userData.json();
      
      await env.CACHE_SERVICE.fetch(new Request('https://internal/cache/set', {
        method: 'POST',
        body: JSON.stringify({
          key: cacheKey,
          value: user,
          ttl: 300
        }),
        headers: internalJsonHeaders(env)
      }));
      
      await env.ANALYTICS_SERVICE.fetch(new Request('https://internal/analytics/track', {
        method: 'POST',
        body: JSON.stringify({
          event: 'user_profile_view',
          userId,
          timestamp: Date.now()
        }),
        headers: internalJsonHeaders(env)
      }));
      
      return new Response(JSON.stringify(user), {
        status: 200,
        headers: { 'Content-Type': 'application/json', 'X-Cache': 'MISS' }
      });
    }
    
    if (method === 'PUT' && url.pathname.startsWith('/user/update')) {
      const body = await request.json();
      const userId = url.pathname.split('/').pop();
      
      const updateResponse = await env.DATA_SERVICE.fetch(new Request(`https://internal/data/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(body),
        headers: internalJsonHeaders(env)
      }));
      
      const updated = await updateResponse.json();
      
      await env.CACHE_SERVICE.fetch(new Request('https://internal/cache/delete', {
        method: 'DELETE',
        body: JSON.stringify({ key: `user:${userId}` }),
        headers: internalJsonHeaders(env)
      }));
      
      await env.ANALYTICS_SERVICE.fetch(new Request('https://internal/analytics/track', {
        method: 'POST',
        body: JSON.stringify({
          event: 'user_profile_updated',
          userId,
          changes: Object.keys(body),
          timestamp: Date.now()
        }),
        headers: internalJsonHeaders(env)
      }));
      
      return new Response(JSON.stringify(updated), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (method === 'POST' && url.pathname === '/user/activity') {
      const body = await request.json();
      return new Response(JSON.stringify({ ok: true, received: body }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Invalid user endpoint' }), {
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

function internalJsonHeaders(env) {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  if (env.INTERNAL_SERVICE_TOKEN) headers.set('X-Internal-Token', env.INTERNAL_SERVICE_TOKEN);
  return headers;
}