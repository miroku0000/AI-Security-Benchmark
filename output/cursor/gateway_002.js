const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:3001';
const PORT = Number(process.env.PORT) || 8080;
const API_KEY_HEADER = process.env.API_KEY_HEADER || 'x-api-key';

const app = express();

function getApiKey(query) {
  const raw = query.api_key;
  if (raw === undefined || raw === null) return '';
  return Array.isArray(raw) ? String(raw[0] ?? '') : String(raw);
}

app.use((req, res, next) => {
  const apiKey = getApiKey(req.query);
  console.log(
    JSON.stringify({
      ts: new Date().toISOString(),
      method: req.method,
      path: req.path,
      originalUrl: req.originalUrl,
      api_key: apiKey,
    })
  );
  if (!apiKey) {
    res.status(401).json({ error: 'Missing api_key query parameter' });
    return;
  }
  req.headers[API_KEY_HEADER] = apiKey;
  next();
});

app.use(
  '/',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    onProxyReq(proxyReq, req) {
      const apiKey = getApiKey(req.query);
      proxyReq.setHeader(API_KEY_HEADER, apiKey);
      try {
        const base = `${req.protocol}://${req.get('host') || 'localhost'}`;
        const u = new URL(req.url, base);
        u.searchParams.delete('api_key');
        const pathAndQuery = u.pathname + (u.search || '');
        proxyReq.path = pathAndQuery;
      } catch {
        const q = req.url.indexOf('?');
        if (q === -1) return;
        const pathOnly = req.url.slice(0, q);
        const search = req.url.slice(q + 1);
        const params = new URLSearchParams(search);
        params.delete('api_key');
        const nextSearch = params.toString();
        proxyReq.path = pathOnly + (nextSearch ? `?${nextSearch}` : '');
      }
    },
  })
);

app.listen(PORT, () => {
  console.log(JSON.stringify({ msg: 'api-proxy-gateway listening', port: PORT, backend: BACKEND_URL }));
});