const express = require('express');
const http = require('http');
const https = require('https');
const dns = require('dns');
const net = require('net');

const app = express();

const PORT = Number(process.env.PORT || 8080);
const REQUEST_TIMEOUT_MS = Number(process.env.REQUEST_TIMEOUT_MS || 30000);
const MAX_REQUEST_SIZE = process.env.MAX_REQUEST_SIZE || '10mb';
const API_KEY = process.env.PROXY_API_KEY || '';
const ALLOWED_HOSTS = (process.env.ALLOWED_HOSTS || '')
  .split(',')
  .map((host) => host.trim().toLowerCase())
  .filter(Boolean);

const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'host',
  'content-length'
]);

app.disable('x-powered-by');
app.use(express.raw({ type: () => true, limit: MAX_REQUEST_SIZE }));

function normalizeHostname(hostname) {
  return hostname.replace(/^\[|\]$/g, '').toLowerCase();
}

function parseIPv4(ip) {
  const parts = ip.split('.');
  if (parts.length !== 4) return null;
  const octets = parts.map((part) => Number(part));
  if (octets.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) return null;
  return octets;
}

function isPrivateIPv4(ip) {
  const octets = parseIPv4(ip);
  if (!octets) return false;
  const [a, b] = octets;

  if (a === 0) return true;
  if (a === 10) return true;
  if (a === 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  if (a === 192 && b === 0) return true;
  if (a === 198 && (b === 18 || b === 19)) return true;
  if (a >= 224) return true;

  return false;
}

function isPrivateIPv6(ip) {
  const normalized = ip.toLowerCase().split('%')[0];

  if (normalized === '::1' || normalized === '::') return true;
  if (normalized.startsWith('fc') || normalized.startsWith('fd')) return true;
  if (normalized.startsWith('fe8') || normalized.startsWith('fe9') || normalized.startsWith('fea') || normalized.startsWith('feb')) return true;
  if (normalized.startsWith('2001:db8:')) return true;

  const mapped = normalized.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
  if (mapped) return isPrivateIPv4(mapped[1]);

  return false;
}

function isBlockedIp(ip) {
  const family = net.isIP(ip);
  if (family === 4) return isPrivateIPv4(ip);
  if (family === 6) return isPrivateIPv6(ip);
  return true;
}

function isAllowedHostname(hostname) {
  if (ALLOWED_HOSTS.length === 0) return true;
  return ALLOWED_HOSTS.some((allowed) => hostname === allowed || hostname.endsWith(`.${allowed}`));
}

function validateTargetUrl(rawUrl) {
  if (typeof rawUrl !== 'string' || rawUrl.trim() === '') {
    throw new Error('Missing target URL');
  }

  let target;
  try {
    target = new URL(rawUrl);
  } catch {
    throw new Error('Invalid target URL');
  }

  if (!['http:', 'https:'].includes(target.protocol)) {
    throw new Error('Only http and https URLs are allowed');
  }

  if (target.username || target.password) {
    throw new Error('Target URL must not include credentials');
  }

  const hostname = normalizeHostname(target.hostname);
  if (!hostname) {
    throw new Error('Invalid target hostname');
  }

  if (!isAllowedHostname(hostname)) {
    throw new Error('Target hostname is not allowed');
  }

  if (
    hostname === 'localhost' ||
    hostname.endsWith('.localhost') ||
    hostname.endsWith('.local') ||
    hostname.endsWith('.internal') ||
    hostname === 'metadata.google.internal'
  ) {
    throw new Error('Target hostname is not allowed');
  }

  if (net.isIP(hostname) && isBlockedIp(hostname)) {
    throw new Error('Target IP address is not allowed');
  }

  return target;
}

function safeLookup(hostname, options, callback) {
  dns.lookup(hostname, { all: true, verbatim: true }, (err, addresses) => {
    if (err) {
      callback(err);
      return;
    }

    const safeAddresses = addresses.filter((entry) => !isBlockedIp(entry.address));
    if (safeAddresses.length === 0) {
      callback(new Error('Target resolved to a blocked IP address'));
      return;
    }

    const requestedFamily =
      options && typeof options === 'object' && Number.isInteger(options.family) && options.family !== 0
        ? options.family
        : 0;

    const selected =
      safeAddresses.find((entry) => entry.family === requestedFamily) ||
      safeAddresses[0];

    callback(null, selected.address, selected.family);
  });
}

function buildUpstreamHeaders(req, target) {
  const headers = {};

  for (const [key, value] of Object.entries(req.headers)) {
    const lowerKey = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lowerKey)) continue;
    if (lowerKey === 'x-target-url' || lowerKey === 'x-api-key') continue;
    headers[key] = value;
  }

  headers.host = target.host;
  headers['x-forwarded-proto'] = req.protocol;
  headers['x-forwarded-host'] = req.get('host') || '';
  headers['x-forwarded-for'] = req.ip || req.socket.remoteAddress || '';

  const hasBody = req.body && req.body.length > 0 && req.method !== 'GET' && req.method !== 'HEAD';
  if (hasBody) {
    headers['content-length'] = String(req.body.length);
  }

  return headers;
}

function sendError(res, status, message) {
  if (!res.headersSent) {
    res.status(status).json({ error: message });
  } else {
    res.end();
  }
}

app.get('/healthz', (_req, res) => {
  res.status(200).json({ ok: true });
});

app.all('/proxy', async (req, res) => {
  if (API_KEY && req.get('x-api-key') !== API_KEY) {
    sendError(res, 401, 'Unauthorized');
    return;
  }

  if (req.method === 'CONNECT' || req.method === 'TRACE') {
    sendError(res, 405, 'Method not allowed');
    return;
  }

  let target;
  try {
    target = validateTargetUrl(req.query.url || req.get('x-target-url'));
  } catch (err) {
    sendError(res, 400, err.message);
    return;
  }

  try {
    const lookupResults = await dns.promises.lookup(normalizeHostname(target.hostname), {
      all: true,
      verbatim: true
    });

    if (lookupResults.length === 0 || lookupResults.some((entry) => isBlockedIp(entry.address))) {
      throw new Error('Target resolved to a blocked IP address');
    }
  } catch (err) {
    sendError(res, 400, err.message || 'Target hostname could not be resolved');
    return;
  }

  const isHttps = target.protocol === 'https:';
  const client = isHttps ? https : http;
  const headers = buildUpstreamHeaders(req, target);

  const requestOptions = {
    protocol: target.protocol,
    hostname: normalizeHostname(target.hostname),
    port: target.port || (isHttps ? 443 : 80),
    method: req.method,
    path: `${target.pathname}${target.search}`,
    headers,
    lookup: safeLookup
  };

  const upstreamReq = client.request(requestOptions, (upstreamRes) => {
    for (const [key, value] of Object.entries(upstreamRes.headers)) {
      if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    }

    res.status(upstreamRes.statusCode || 502);

    upstreamRes.on('error', (err) => {
      if (!res.headersSent) {
        sendError(res, 502, err.message || 'Upstream response error');
      } else {
        res.destroy(err);
      }
    });

    upstreamRes.pipe(res);
  });

  upstreamReq.setTimeout(REQUEST_TIMEOUT_MS, () => {
    upstreamReq.destroy(new Error('Upstream request timed out'));
  });

  upstreamReq.on('error', (err) => {
    sendError(res, 502, err.message || 'Proxy request failed');
  });

  const hasBody = req.body && req.body.length > 0 && req.method !== 'GET' && req.method !== 'HEAD';
  if (hasBody) {
    upstreamReq.end(req.body);
  } else {
    upstreamReq.end();
  }
});

app.use((_req, res) => {
  sendError(res, 404, 'Not found');
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Webhook proxy listening on port ${PORT}`);
  });
}

module.exports = app;