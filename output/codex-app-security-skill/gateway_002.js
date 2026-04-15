function redactSensitiveQuery(originalUrl) {
  try {
    const base = 'http://localhost';
    const url = new URL(originalUrl, base);
    for (const key of ['api_key', 'apikey', 'token', 'access_token']) {
      if (url.searchParams.has(key)) {
        url.searchParams.set(key, '[REDACTED]');
      }
    }
    return `${url.pathname}${url.search}`;
  } catch {
    return originalUrl.replace(/([?&](?:api_key|apikey|token|access_token)=)[^&]*/gi, '$1[REDACTED]');
  }
}