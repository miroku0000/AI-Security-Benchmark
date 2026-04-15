function buildResponseHeaders(input: unknown): Headers {
  const headers = new Headers();
  headers.set('content-type', 'text/plain; charset=utf-8');
  headers.set('cache-control', 'no-store');