const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

// Backend service routing configuration
const SERVICES = {
  '/api/users': process.env.USERS_SERVICE_URL || 'http://localhost:4001',
  '/api/orders': process.env.ORDERS_SERVICE_URL || 'http://localhost:4002',
  '/api/products': process.env.PRODUCTS_SERVICE_URL || 'http://localhost:4003',
};

// Valid API keys (in production, load from a secure store)
const VALID_API_KEYS = new Set(
  (process.env.API_KEYS || 'default-dev-key').split(',')
);

// Request logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  const apiKey = req.query.api_key || req.headers['x-api-key'] || 'none';
  console.log(JSON.stringify({
    timestamp,
    method: req.method,
    path: req.path,
    query: req.query,
    ip: req.ip,
    api_key_present: apiKey !== 'none',
  }));
  next();
});

// API key authentication middleware
app.use((req, res, next) => {
  const apiKey = req.query.api_key || req.headers['x-api-key'];

  if (!apiKey) {
    return res.status(401).json({ error: 'API key required. Pass via ?api_key= or x-api-key header.' });
  }

  if (!VALID_API_KEYS.has(apiKey)) {
    return res.status(403).json({ error: 'Invalid API key.' });
  }

  // Forward the API key as a header to backend services, remove from query string
  req.headers['x-api-key'] = apiKey;
  next();
});

// Set up proxy routes for each backend service
for (const [path, target] of Object.entries(SERVICES)) {
  app.use(
    path,
    createProxyMiddleware({
      target,
      changeOrigin: true,
      on: {
        proxyReq: (proxyReq, req) => {
          // Ensure API key header is forwarded
          if (req.headers['x-api-key']) {
            proxyReq.setHeader('x-api-key', req.headers['x-api-key']);
          }
        },
        error: (err, req, res) => {
          console.error(`Proxy error for ${req.path}:`, err.message);
          res.status(502).json({ error: 'Bad gateway', service: req.path });
        },
      },
    })
  );
}

// Health check (no auth required - placed after proxy routes intentionally,
// override with a direct route before auth if needed)
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', services: Object.keys(SERVICES) });
});

app.listen(PORT, () => {
  console.log(`API Gateway listening on port ${PORT}`);
});