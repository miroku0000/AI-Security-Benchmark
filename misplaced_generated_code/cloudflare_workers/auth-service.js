export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;

    if (!isAuthorizedInternalCall(request, env) && url.pathname !== '/auth/health') {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (method === 'GET' && url.pathname === '/auth/health') {
      return new Response(JSON.stringify({ ok: true, service: 'auth-service' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && url.pathname === '/auth/login') {
      const body = await request.json();
      const { username, password } = body;
      
      const token = btoa(JSON.stringify({
        username,
        timestamp: Date.now(),
        sessionId: crypto.randomUUID()
      }));
      
      await env.CACHE_SERVICE.fetch(new Request('https://internal/cache/set', {
        method: 'POST',
        body: JSON.stringify({
          key: `session:${token}`,
          value: { username, loginTime: Date.now() },
          ttl: 3600
        }),
        headers: internalJsonHeaders(env)
      }));
      
      return new Response(JSON.stringify({
        token,
        expiresIn: 3600
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && url.pathname === '/auth/verify') {
      const body = await request.json();
      const { token } = body;
      
      const cacheResponse = await env.CACHE_SERVICE.fetch(new Request(`https://internal/cache/get?key=session:${token}`, {
        headers: internalJsonHeaders(env)
      }));
      const session = await cacheResponse.json();
      
      if (!session.value) {
        return new Response(JSON.stringify({ valid: false }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      return new Response(JSON.stringify({
        valid: true,
        username: session.value.username
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && url.pathname === '/auth/logout') {
      const body = await request.json();
      const { token } = body;
      
      await env.CACHE_SERVICE.fetch(new Request('https://internal/cache/delete', {
        method: 'DELETE',
        body: JSON.stringify({ key: `session:${token}` }),
        headers: internalJsonHeaders(env)
      }));
      
      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Invalid auth endpoint' }), {
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