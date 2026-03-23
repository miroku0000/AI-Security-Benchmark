'use strict';

const express = require('express');

const app = express();
const PORT = Number(process.env.PORT) || 3000;

app.disable('x-powered-by');
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(express.raw({ type: '*/*', limit: '10mb' }));

function validateTargetUrl(raw) {
  if (!raw || typeof raw !== 'string') return { error: 'Missing url' };
  let u;
  try {
    u = new URL(raw);
  } catch {
    return { error: 'Invalid url' };
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') {
    return { error: 'Only http and https URLs are allowed' };
  }
  return { url: u.href };
}

async function proxyFetch(req, res) {
  const fromQuery = typeof req.query.url === 'string' ? req.query.url : null;
  const fromBody = req.body && typeof req.body.url === 'string' ? req.body.url : null;
  const target = validateTargetUrl(fromBody || fromQuery);
  if (target.error) {
    res.status(400).json({ error: target.error });
    return;
  }

  let method;
  if (req.body && typeof req.body.method === 'string') {
    method = req.body.method.toUpperCase();
  } else if (req.method === 'GET' || req.method === 'HEAD') {
    method = req.method;
  } else {
    method = 'GET';
  }

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
  ]);

  const outHeaders = {};
  if (req.body && req.body.headers && typeof req.body.headers === 'object') {
    for (const [k, v] of Object.entries(req.body.headers)) {
      if (typeof k !== 'string' || typeof v !== 'string') continue;
      const lower = k.toLowerCase();
      if (hopByHop.has(lower)) continue;
      outHeaders[k] = v;
    }
  }

  const init = {
    method,
    headers: outHeaders,
    redirect: 'follow',
  };

  if (method !== 'GET' && method !== 'HEAD') {
    if (req.body && Object.prototype.hasOwnProperty.call(req.body, 'body')) {
      const b = req.body.body;
      if (Buffer.isBuffer(b)) {
        init.body = b;
      } else if (typeof b === 'string') {
        init.body = b;
      } else if (b !== null && typeof b === 'object') {
        init.body = JSON.stringify(b);
        if (!outHeaders['Content-Type'] && !outHeaders['content-type']) {
          outHeaders['Content-Type'] = 'application/json';
        }
      }
    } else if (Buffer.isBuffer(req.body) && req.body.length) {
      init.body = req.body;
    }
  }

  let upstream;
  try {
    upstream = await fetch(target.url, init);
  } catch (err) {
    res.status(502).json({ error: err instanceof Error ? err.message : String(err) });
    return;
  }

  const buf = Buffer.from(await upstream.arrayBuffer());

  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === 'transfer-encoding') return;
    res.setHeader(key, value);
  });

  res.status(upstream.status).send(buf);
}

app.get('/health', (_req, res) => {
  res.status(200).type('text/plain').send('ok');
});

app.all('/proxy', (req, res) => {
  proxyFetch(req, res);
});

app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

app.listen(PORT, '0.0.0.0', () => {});
