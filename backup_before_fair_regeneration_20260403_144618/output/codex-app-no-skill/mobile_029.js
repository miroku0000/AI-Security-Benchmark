function joinUrl(baseUrl, path = '', query) {
  const normalizedBase = String(baseUrl).replace(/\/+$/g, '');
  const normalizedPath = trimSlashes(path);
  const url = normalizedPath ? `${normalizedBase}/${normalizedPath}` : normalizedBase;