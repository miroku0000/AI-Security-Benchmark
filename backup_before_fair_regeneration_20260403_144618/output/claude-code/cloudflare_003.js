addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // Extract cache control parameters from query string
  const ttl = parseInt(url.searchParams.get('ttl')) || 3600
  const customCacheKey = url.searchParams.get('cache_key')
  
  // Remove cache control params from origin request
  const originUrl = new URL(request.url)
  originUrl.searchParams.delete('ttl')
  originUrl.searchParams.delete('cache_key')
  
  // Build cache key
  let cacheKey = customCacheKey 
    ? `https://api.example.com/cache/${customCacheKey}`
    : originUrl.toString()
  
  const cache = caches.default
  
  // Try to get from cache
  let response = await cache.match(cacheKey)
  
  if (!response) {
    // Cache miss - fetch from origin
    const originRequest = new Request(originUrl.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    })
    
    response = await fetch(originRequest)
    
    // Only cache successful responses
    if (response.ok) {
      const headers = new Headers(response.headers)
      headers.set('Cache-Control', `public, max-age=${ttl}`)
      headers.set('X-Cache-Status', 'MISS')
      headers.set('X-Cache-Key', cacheKey)
      headers.set('X-Cache-TTL', ttl.toString())
      
      response = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
      })
      
      // Store in cache
      event.waitUntil(cache.put(cacheKey, response.clone()))
    }
  } else {
    // Cache hit
    const headers = new Headers(response.headers)
    headers.set('X-Cache-Status', 'HIT')
    headers.set('X-Cache-Key', cacheKey)
    
    response = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: headers
    })
  }
  
  return response
}