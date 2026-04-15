addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Handle CORS preflight requests
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
        'Access-Control-Max-Age': '86400',
      }
    })
  }

  // Get the backend URL from environment variable or use default
  const BACKEND_URL = typeof BACKEND_URL !== 'undefined' ? BACKEND_URL : 'https://api.example.com'
  
  // Parse the URL to get the path
  const url = new URL(request.url)
  const backendUrl = BACKEND_URL + url.pathname + url.search

  // Create new headers from the request, removing CF-specific headers
  const headers = new Headers(request.headers)
  headers.delete('cf-connecting-ip')
  headers.delete('cf-ray')
  headers.delete('cf-visitor')
  headers.delete('cf-ipcountry')
  
  // Forward the request to backend
  const backendRequest = new Request(backendUrl, {
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: 'follow'
  })

  try {
    // Fetch from backend
    const backendResponse = await fetch(backendRequest)
    
    // Clone the response to modify headers
    const response = new Response(backendResponse.body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: backendResponse.headers
    })
    
    // Add CORS headers to response
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin')
    
    return response
  } catch (error) {
    // Return error response with CORS headers
    return new Response(JSON.stringify({ error: 'Backend service unavailable', details: error.message }), {
      status: 502,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
      }
    })
  }
}