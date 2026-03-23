'use strict';

const express = require('express');
const { URL } = require('url');

const app = express();
const PORT = process.env.PORT || 3000;

const hopByHop = new Set([
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

function isAllowedUrl(u) {
  try {
    const parsed = new URL(u);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function getTargetUrl(req) {
  const q = req.query.url;
  if (typeof q === 'string' && q) return q;
  const h = req.headers['x-target-url'];
  if (typeof h === 'string' && h) return h;
  return null;
}

app.get('/health', (_req, res) => {
  res.status(200).type('text/plain').send('ok');
});

app.use(
  '/proxy',
  express.raw({ type: '*/*', limit: process.env.BODY_LIMIT || '10mb' }),
);

app.all('/proxy', async (req, res) => {
  const targetUrl = getTargetUrl(req);
  if (!targetUrl || !isAllowedUrl(targetUrl)) {
    res.status(400).type('text/plain').send('Bad or missing url (use ?url= or X-Target-URL)');
    return;
  }

  const method = req.method;
  const headers = {};
  for (const [key, val] of Object.entries(req.headers)) {
    const lower = key.toLowerCase();
    if (hopByHop.has(lower)) continue;
    if (lower === 'x-target-url') continue;
    if (val === undefined) continue;
    if (Array.isArray(val)) headers[key] = val.join(', ');
    else headers[key] = val;
  }

  let body;
  if (method !== 'GET' && method !== 'HEAD') {
    if (Buffer.isBuffer(req.body) && req.body.length) body = req.body;
  }

  let upstream;
  try {
    upstream = await fetch(targetUrl, {
      method,
      headers,
      body,
      redirect: 'follow',
    });
  } catch (err) {
    res.status(502).type('text/plain').send(err.message || String(err));
    return;
  }

  res.status(upstream.status);
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === 'transfer-encoding') return;
    res.append(key, value);
  });

  const buf = Buffer.from(await upstream.arrayBuffer());
  res.send(buf);
});

app.listen(PORT, () => {
  process.stdout.write(`listening on ${PORT}\n`);
});
