'use strict';

const express = require('express');
const { Readable } = require('stream');
const { pipeline } = require('stream/promises');

const app = express();
const PORT = process.env.PORT || 3000;
const REQUEST_TIMEOUT_MS = Number(process.env.REQUEST_TIMEOUT_MS) || 30000;

const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
  'host',
  'content-length',
]);

function sanitizeRequestHeaders(headers) {
  const out = {};
  for (const [key, value] of Object.entries(headers)) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP.has(lower)) continue;
    out[key] = value;
  }
  return out;
}

function getTargetUrl(req) {
  if (req.query && req.query.url) return String(req.query.url);
  if (Buffer.isBuffer(req.body) && req.body.length) {
    const ct = (req.headers['content-type'] || '').toLowerCase();
    if (ct.includes('application/json')) {
      try {
        const parsed = JSON.parse(req.body.toString('utf8'));
        if (parsed && typeof parsed === 'object' && parsed.url) {
          return String(parsed.url);
        }
      } catch (_) {
        /* ignore */
      }
    }
  }
  return null;
}

function buildUpstreamBody(req, targetUrl) {
  if (req.method === 'GET' || req.method === 'HEAD') return undefined;
  if (!Buffer.isBuffer(req.body) || !req.body.length) return undefined;

  const ct = (req.headers['content-type'] || '').toLowerCase();
  if (!ct.includes('application/json')) {
    return req.body;
  }

  try {
    const parsed = JSON.parse(req.body.toString('utf8'));
    if (!parsed || typeof parsed !== 'object') return req.body;
    if (String(parsed.url) !== targetUrl) return req.body;
    const { url: _u, ...rest } = parsed;
    if (Object.keys(rest).length === 0) return undefined;
    return Buffer.from(JSON.stringify(rest), 'utf8');
  } catch (_) {
    return req.body;
  }
}

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

app.use((req, res, next) => {
  if (req.path === '/proxy' || req.path.startsWith('/proxy/')) {
    return express.raw({ type: '*/*', limit: '50mb' })(req, res, next);
  }
  next();
});

app.all('/proxy', async (req, res) => {
  const targetUrl = getTargetUrl(req);
  if (!targetUrl) {
    return res.status(400).json({
      error: 'Missing url: use ?url= or JSON body { "url": "https://..." }',
    });
  }

  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return res.status(400).json({ error: 'Invalid url' });
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return res.status(400).json({ error: 'Only http and https URLs are allowed' });
  }

  const upstreamHeaders = sanitizeRequestHeaders(req.headers);
  const body = buildUpstreamBody(req, targetUrl);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: upstreamHeaders,
      body,
      redirect: 'manual',
      signal: controller.signal,
    });

    upstream.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (
        lower === 'content-encoding' ||
        lower === 'content-length' ||
        lower === 'transfer-encoding'
      ) {
        return;
      }
      res.setHeader(key, value);
    });

    res.status(upstream.status);

    if (!upstream.body) {
      return res.end();
    }

    const nodeStream = Readable.fromWeb(upstream.body);
    await pipeline(nodeStream, res);
  } catch (err) {
    const msg = err && err.name === 'AbortError' ? 'Upstream request timed out' : (err && err.message) || 'Proxy request failed';
    if (!res.headersSent) {
      res.status(502).json({ error: 'Proxy request failed', message: msg });
    } else {
      res.end();
    }
  } finally {
    clearTimeout(timeout);
  }
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Webhook proxy listening on port ${PORT}`);
  });
}

module.exports = app;
