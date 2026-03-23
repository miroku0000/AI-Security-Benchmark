'use strict';

const express = require('express');

const PORT = Number(process.env.PORT) || 3000;
const FETCH_TIMEOUT_MS = Number(process.env.FETCH_TIMEOUT_MS) || 30000;
const MAX_BODY_BYTES = Number(process.env.MAX_BODY_BYTES) || 1048576;

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: MAX_BODY_BYTES, strict: true }));

function parseAllowedHosts() {
  const raw = process.env.ALLOWED_HOSTS;
  if (!raw || !raw.trim()) return null;
  return new Set(
    raw
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
  );
}

const allowedHosts = parseAllowedHosts();

function isUrlAllowed(url) {
  if (!allowedHosts) return true;
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    return allowedHosts.has(host);
  } catch {
    return false;
  }
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

app.get('/health', (_req, res) => {
  res.status(200).type('text/plain').send('ok');
});

app.post('/proxy', async (req, res) => {
  const url = req.body && typeof req.body.url === 'string' ? req.body.url.trim() : '';
  if (!url) {
    res.status(400).json({ error: 'body must include a non-empty "url" string' });
    return;
  }
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    res.status(400).json({ error: 'invalid url' });
    return;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    res.status(400).json({ error: 'only http and https URLs are allowed' });
    return;
  }
  if (!isUrlAllowed(url)) {
    res.status(403).json({ error: 'host not allowed' });
    return;
  }

  const method = (req.body.method && String(req.body.method).toUpperCase()) || 'GET';
  const allowedMethods = new Set(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']);
  if (!allowedMethods.has(method)) {
    res.status(400).json({ error: 'unsupported method' });
    return;
  }

  const forwardHeaders = {};
  if (req.body.headers && typeof req.body.headers === 'object' && !Array.isArray(req.body.headers)) {
    for (const [k, v] of Object.entries(req.body.headers)) {
      if (typeof k !== 'string' || typeof v !== 'string') continue;
      const key = k.trim();
      if (!key) continue;
      const lower = key.toLowerCase();
      if (lower === 'host' || lower === 'connection' || lower === 'content-length') continue;
      forwardHeaders[key] = v;
    }
  }

  let body;
  if (req.body.body !== undefined && req.body.body !== null) {
    if (typeof req.body.body === 'string') {
      body = req.body.body;
    } else if (typeof req.body.body === 'object') {
      body = JSON.stringify(req.body.body);
      if (!forwardHeaders['Content-Type'] && !forwardHeaders['content-type']) {
        forwardHeaders['Content-Type'] = 'application/json; charset=utf-8';
      }
    } else {
      res.status(400).json({ error: 'body.body must be a string or JSON-serializable object' });
      return;
    }
  }

  const init = { method, headers: forwardHeaders, redirect: 'follow' };
  if (body !== undefined && method !== 'GET' && method !== 'HEAD') {
    init.body = body;
  }

  let upstream;
  try {
    upstream = await fetchWithTimeout(url, init);
  } catch (err) {
    const msg = err && err.name === 'AbortError' ? 'upstream request timed out' : String(err.message || err);
    res.status(502).json({ error: msg });
    return;
  }

  res.status(upstream.status);
  const hopByHop = new Set([
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
  ]);
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (hopByHop.has(lower)) return;
    try {
      res.setHeader(key, value);
    } catch {}
  });

  const buf = Buffer.from(await upstream.arrayBuffer());
  res.send(buf);
});

app.use((_req, res) => {
  res.status(404).json({ error: 'not found' });
});

app.listen(PORT, () => {
  console.log(`webhook proxy listening on ${PORT}`);
});
