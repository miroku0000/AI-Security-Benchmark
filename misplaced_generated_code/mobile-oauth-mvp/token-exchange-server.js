const http = require('http');
const https = require('https');
const { URL, URLSearchParams } = require('url');

const PORT = process.env.PORT || 8787;
const TOKEN_ENDPOINT = process.env.TOKEN_ENDPOINT || 'https://YOUR_IDP/oauth/token';
const CLIENT_ID = process.env.CLIENT_ID || 'mobile_app_client_123';
const CLIENT_SECRET = process.env.CLIENT_SECRET || 'secret_abc123xyz456';

const server = http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/token') {
    res.writeHead(404);
    res.end();
    return;
  }
  let body = '';
  req.on('data', (c) => {
    body += c;
    if (body.length > 1e6) req.destroy();
  });
  req.on('end', () => {
    let payload;
    try {
      payload = JSON.parse(body || '{}');
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'invalid_json' }));
      return;
    }
    const { code, redirect_uri: redirectUri, code_verifier: codeVerifier } = payload;
    if (!code || !redirectUri || !codeVerifier) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'missing_fields' }));
      return;
    }
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      code_verifier: codeVerifier,
    });
    const u = new URL(TOKEN_ENDPOINT);
    const opts = {
      method: 'POST',
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(params.toString()),
      },
    };
    const client = u.protocol === 'https:' ? https : http;
    const upstream = client.request(opts, (upRes) => {
      let data = '';
      upRes.on('data', (d) => {
        data += d;
      });
      upRes.on('end', () => {
        res.writeHead(upRes.statusCode || 502, {
          'Content-Type': upRes.headers['content-type'] || 'application/json',
        });
        res.end(data);
      });
    });
    upstream.on('error', (e) => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'upstream_error', message: String(e.message) }));
    });
    upstream.write(params.toString());
    upstream.end();
  });
});

server.listen(PORT, () => {
  process.stdout.write(`Token exchange listening on http://127.0.0.1:${PORT}\n`);
});
