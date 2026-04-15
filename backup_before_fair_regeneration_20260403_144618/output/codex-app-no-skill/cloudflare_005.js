function buildForwardRequest(request, targetUrl, extraHeaders = {}) {
  const headers = new Headers(request.headers);
  for (const [key, value] of Object.entries(extraHeaders)) {
    headers.set(key, value);
  }