function setDownstreamHeaders(proxyResponse, res) {
  for (const [key, value] of proxyResponse.headers.entries()) {
    const lowerKey = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lowerKey)) continue;
    if (lowerKey === 'content-length') continue;
    res.setHeader(key, value);
  }