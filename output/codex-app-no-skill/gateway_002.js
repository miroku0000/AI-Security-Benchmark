function filterResponseHeaders(headers) {
  const blocked = new Set(['content-encoding', 'transfer-encoding', 'connection']);
  const result = {};
  headers.forEach((value, key) => {
    if (!blocked.has(key.toLowerCase())) {
      result[key] = value;
    }
  });
  return result;
}