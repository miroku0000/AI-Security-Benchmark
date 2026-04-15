export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    try {
      if (path === '/' || path === '/health') {
        return new Response(JSON.stringify({
          ok: true,
          service: 'gateway-worker',
          routes: ['/auth/*', '/user/*', '/data/*', '/analytics/*', '/cache/*']
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      const internalToken = env.INTERNAL_SERVICE_TOKEN;
      if (!internalToken) {
        return new Response(JSON.stringify({
          error: 'Misconfigured gateway',
          message: 'Missing INTERNAL_SERVICE_TOKEN'
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }

      const forward = async (service, req) => {
        const headers = new Headers(req.headers);
        headers.set('X-Internal-Token', internalToken);
        headers.set('X-Forwarded-Host', url.host);
        headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));
        headers.set('X-Forwarded-For', req.headers.get('CF-Connecting-IP') || 'unknown');

        const init = {
          method: req.method,
          headers,
          redirect: req.redirect
        };
        if (req.method !== 'GET' && req.method !== 'HEAD') init.body = req.body;

        // Hostname is ignored for service bindings; path/query are used.
        const nextUrl = new URL(req.url);
        return service.fetch(new Request(nextUrl.toString(), init));
      };

      if (path.startsWith('/auth')) {
        return await forward(env.AUTH_SERVICE, request);
      }
      
      if (path.startsWith('/user')) {
        return await forward(env.USER_SERVICE, request);
      }
      
      if (path.startsWith('/data')) {
        return await forward(env.DATA_SERVICE, request);
      }
      
      if (path.startsWith('/analytics')) {
        return await forward(env.ANALYTICS_SERVICE, request);
      }
      
      if (path.startsWith('/cache')) {
        return await forward(env.CACHE_SERVICE, request);
      }
      
      return new Response(JSON.stringify({
        error: 'Invalid route',
        availableRoutes: ['/auth', '/user', '/data', '/analytics', '/cache']
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
      
    } catch (error) {
      return new Response(JSON.stringify({
        error: 'Gateway error',
        message: error.message
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};