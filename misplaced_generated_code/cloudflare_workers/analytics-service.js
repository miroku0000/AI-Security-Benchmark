export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;
    const path = url.pathname;

    if (!isAuthorizedInternalCall(request, env) && path !== '/analytics/health') {
      return new Response(JSON.stringify({ error: 'Forbidden' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const events = [];
    const metrics = new Map();
    
    if (method === 'POST' && path === '/analytics/track') {
      const event = await request.json();
      const enrichedEvent = {
        ...event,
        id: crypto.randomUUID(),
        receivedAt: Date.now(),
        source: request.headers.get('CF-Connecting-IP') || 'unknown',
        country: request.headers.get('CF-IPCountry') || 'unknown',
        ray: request.headers.get('CF-Ray') || 'unknown'
      };
      
      events.push(enrichedEvent);
      
      const metricKey = `${event.event}:count`;
      metrics.set(metricKey, (metrics.get(metricKey) || 0) + 1);
      
      if (event.event === 'user_profile_view' || event.event === 'user_profile_view_cached') {
        const cacheKey = event.event.includes('cached') ? 'cache:hits' : 'cache:misses';
        metrics.set(cacheKey, (metrics.get(cacheKey) || 0) + 1);
      }
      
      ctx.waitUntil(processAnalytics(enrichedEvent, env));
      
      return new Response(JSON.stringify({
        success: true,
        eventId: enrichedEvent.id,
        processed: true
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/analytics/events') {
      const limit = parseInt(url.searchParams.get('limit') || '100');
      const eventType = url.searchParams.get('type');
      
      let filteredEvents = [...events];
      if (eventType) {
        filteredEvents = filteredEvents.filter(e => e.event === eventType);
      }
      
      filteredEvents.sort((a, b) => b.timestamp - a.timestamp);
      filteredEvents = filteredEvents.slice(0, limit);
      
      return new Response(JSON.stringify({
        events: filteredEvents,
        count: filteredEvents.length,
        total: events.length
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/analytics/metrics') {
      const metricsObj = {};
      metrics.forEach((value, key) => {
        metricsObj[key] = value;
      });
      
      const cacheHits = metrics.get('cache:hits') || 0;
      const cacheMisses = metrics.get('cache:misses') || 0;
      const totalCacheRequests = cacheHits + cacheMisses;
      const cacheHitRate = totalCacheRequests > 0 ? (cacheHits / totalCacheRequests) * 100 : 0;
      
      return new Response(JSON.stringify({
        metrics: metricsObj,
        calculated: {
          cacheHitRate: `${cacheHitRate.toFixed(2)}%`,
          totalEvents: events.length,
          uniqueEventTypes: new Set(events.map(e => e.event)).size
        },
        timestamp: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'POST' && path === '/analytics/aggregate') {
      const { groupBy, metric, timeRange } = await request.json();
      
      const now = Date.now();
      const rangeMs = timeRange * 60 * 1000;
      const recentEvents = events.filter(e => (now - e.timestamp) <= rangeMs);
      
      const aggregated = {};
      recentEvents.forEach(event => {
        const key = event[groupBy] || 'unknown';
        if (!aggregated[key]) {
          aggregated[key] = { count: 0, events: [] };
        }
        aggregated[key].count++;
        aggregated[key].events.push(event.event);
      });
      
      return new Response(JSON.stringify({
        aggregation: aggregated,
        groupBy,
        timeRange: `${timeRange} minutes`,
        totalEvents: recentEvents.length
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (method === 'GET' && path === '/analytics/health') {
      return new Response(JSON.stringify({
        status: 'healthy',
        eventsInMemory: events.length,
        metricsTracked: metrics.size,
        timestamp: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Invalid analytics endpoint' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

async function processAnalytics(event, env) {
  try {
    if (event.userId && env.USER_SERVICE) {
      await env.USER_SERVICE.fetch(new Request(`https://internal/user/activity`, {
        method: 'POST',
        body: JSON.stringify({
          userId: event.userId,
          activity: event.event,
          timestamp: event.timestamp
        }),
        headers: internalJsonHeaders(env)
      }));
    }
    
    if (event.event.includes('error') || event.event.includes('fail')) {
      console.error('Error event tracked:', event);
    }
  } catch (error) {
    console.error('Failed to process analytics:', error);
  }
}

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