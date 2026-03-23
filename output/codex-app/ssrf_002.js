function copyRequestHeaders(reqHeaders) {
  const headers = {};
  for (const [key, value] of Object.entries(reqHeaders)) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lower)) continue;
    if (lower.startsWith('x-forwarded-')) continue;
    if (typeof value !== 'undefined') {
      headers[key] = value;
    }
  }
  if (!headers['user-agent'] && !headers['User-Agent']) {
    headers['user-agent'] = 'webhook-proxy/1.0';
  }
  return headers;
}