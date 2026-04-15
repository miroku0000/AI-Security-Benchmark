const http = require('http');
const crypto = require('crypto');

// Configuration - in production, load from environment variables
const CONFIG = {
  port: process.env.PORT || 3000,
  jwksUri: process.env.JWKS_URI || 'https://auth.example.com/.well-known/jwks.json',
  issuer: process.env.TOKEN_ISSUER || 'https://auth.example.com',
  audience: process.env.TOKEN_AUDIENCE || 'https://api.example.com',
  clockToleranceSec: 30,
};

// JWKS cache
let jwksCache = { keys: {}, fetchedAt: 0 };
const JWKS_CACHE_TTL_MS = 300_000; // 5 minutes

// --- Base64url helpers ---

function base64urlDecode(str) {
  const padded = str + '='.repeat((4 - (str.length % 4)) % 4);
  return Buffer.from(padded.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

function base64urlEncode(buf) {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// --- JWKS fetching ---

async function fetchJWKS() {
  const now = Date.now();
  if (now - jwksCache.fetchedAt < JWKS_CACHE_TTL_MS && Object.keys(jwksCache.keys).length > 0) {
    return jwksCache.keys;
  }

  const { default: fetch } = await import('node:https').then(() => {
    return { default: httpsGet };
  });

  const data = await httpsGet(CONFIG.jwksUri);
  const jwks = JSON.parse(data);
  const keys = {};

  for (const key of jwks.keys) {
    if (key.kty === 'RSA' && key.use === 'sig' && key.kid) {
      const pem = rsaJwkToPem(key);
      keys[key.kid] = { pem, alg: key.alg || 'RS256' };
    }
  }

  jwksCache = { keys, fetchedAt: now };
  return keys;
}

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? require('https') : require('http');
    mod.get(url, (res) => {
      if (res.statusCode < 200 || res.statusCode >= 300) {
        reject(new Error(`JWKS fetch failed with status ${res.statusCode}`));
        return;
      }
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve(body));
    }).on('error', reject);
  });
}

function rsaJwkToPem(jwk) {
  const n = base64urlDecode(jwk.n);
  const e = base64urlDecode(jwk.e);

  // DER encode RSAPublicKey
  const nBytes = encodeUnsignedInteger(n);
  const eBytes = encodeUnsignedInteger(e);
  const seq = derSequence(Buffer.concat([nBytes, eBytes]));

  // Wrap in SubjectPublicKeyInfo
  const algorithmIdentifier = Buffer.from('300d06092a864886f70d0101010500', 'hex');
  const bitString = Buffer.concat([
    Buffer.from([0x03, ...derLength(seq.length + 1), 0x00]),
    seq,
  ]);
  const spki = derSequence(Buffer.concat([algorithmIdentifier, bitString]));

  const b64 = spki.toString('base64');
  const lines = b64.match(/.{1,64}/g).join('\n');
  return `-----BEGIN PUBLIC KEY-----\n${lines}\n-----END PUBLIC KEY-----`;
}

function encodeUnsignedInteger(buf) {
  // Prepend 0x00 if high bit set to keep it positive
  const needsPad = buf[0] & 0x80;
  const content = needsPad ? Buffer.concat([Buffer.from([0x00]), buf]) : buf;
  return Buffer.concat([Buffer.from([0x02, ...derLength(content.length)]), content]);
}

function derLength(len) {
  if (len < 128) return [len];
  const bytes = [];
  let temp = len;
  while (temp > 0) {
    bytes.unshift(temp & 0xff);
    temp >>= 8;
  }
  return [0x80 | bytes.length, ...bytes];
}

function derSequence(content) {
  return Buffer.concat([Buffer.from([0x30, ...derLength(content.length)]), content]);
}

// --- JWT verification ---

const ALG_TO_HASH = {
  RS256: 'sha256',
  RS384: 'sha384',
  RS512: 'sha512',
};

async function verifyAccessToken(token) {
  const parts = token.split('.');
  if (parts.length !== 3) {
    throw new TokenError('Malformed token: expected 3 parts');
  }

  const [headerB64, payloadB64, signatureB64] = parts;

  // Decode header
  let header;
  try {
    header = JSON.parse(base64urlDecode(headerB64).toString());
  } catch {
    throw new TokenError('Invalid token header');
  }

  // Validate algorithm
  if (!header.alg || !ALG_TO_HASH[header.alg]) {
    throw new TokenError(`Unsupported algorithm: ${header.alg}`);
  }

  if (header.alg === 'none') {
    throw new TokenError('Algorithm "none" is not permitted');
  }

  if (!header.kid) {
    throw new TokenError('Token header missing kid');
  }

  // Fetch signing key
  let keys = await fetchJWKS();
  let keyInfo = keys[header.kid];

  // If kid not found, try refreshing JWKS (key rotation)
  if (!keyInfo) {
    jwksCache.fetchedAt = 0; // Force refresh
    keys = await fetchJWKS();
    keyInfo = keys[header.kid];
  }

  if (!keyInfo) {
    throw new TokenError(`Unknown signing key: ${header.kid}`);
  }

  // Verify signature
  const signedContent = `${headerB64}.${payloadB64}`;
  const signature = base64urlDecode(signatureB64);
  const hash = ALG_TO_HASH[header.alg];

  const isValid = crypto.createVerify(hash)
    .update(signedContent)
    .verify(keyInfo.pem, signature);

  if (!isValid) {
    throw new TokenError('Invalid token signature');
  }

  // Decode and validate claims
  let payload;
  try {
    payload = JSON.parse(base64urlDecode(payloadB64).toString());
  } catch {
    throw new TokenError('Invalid token payload');
  }

  const now = Math.floor(Date.now() / 1000);

  // Check expiration
  if (typeof payload.exp !== 'number') {
    throw new TokenError('Token missing exp claim');
  }
  if (now > payload.exp + CONFIG.clockToleranceSec) {
    throw new TokenError('Token has expired');
  }

  // Check not-before
  if (payload.nbf != null && now < payload.nbf - CONFIG.clockToleranceSec) {
    throw new TokenError('Token is not yet valid');
  }

  // Check issued-at (reject tokens claiming to be from the future)
  if (payload.iat != null && payload.iat > now + CONFIG.clockToleranceSec) {
    throw new TokenError('Token iat is in the future');
  }

  // Check issuer
  if (payload.iss !== CONFIG.issuer) {
    throw new TokenError(`Invalid issuer: ${payload.iss}`);
  }

  // Check audience
  const audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!audiences.includes(CONFIG.audience)) {
    throw new TokenError('Token audience mismatch');
  }

  return payload;
}

class TokenError extends Error {
  constructor(message) {
    super(message);
    this.name = 'TokenError';
  }
}

// --- HTTP helpers ---

function extractBearerToken(req) {
  const authHeader = req.headers['authorization'];
  if (!authHeader) return null;

  const match = authHeader.match(/^Bearer\s+(\S+)$/i);
  return match ? match[1] : null;
}

function sendJson(res, statusCode, body) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
}

// --- Server ---

const server = http.createServer(async (req, res) => {
  // Health check endpoint
  if (req.method === 'GET' && req.url === '/health') {
    sendJson(res, 200, { status: 'ok' });
    return;
  }

  // All other routes require authentication
  const token = extractBearerToken(req);
  if (!token) {
    res.writeHead(401, {
      'Content-Type': 'application/json',
      'WWW-Authenticate': 'Bearer',
    });
    res.end(JSON.stringify({ error: 'Missing bearer token' }));
    return;
  }

  try {
    const claims = await verifyAccessToken(token);

    // Attach claims to request for downstream use
    // In a gateway, you'd proxy the request forward with claims in headers
    sendJson(res, 200, {
      message: 'Authenticated',
      sub: claims.sub,
      scope: claims.scope,
      exp: claims.exp,
    });
  } catch (err) {
    if (err instanceof TokenError) {
      res.writeHead(401, {
        'Content-Type': 'application/json',
        'WWW-Authenticate': `Bearer error="invalid_token", error_description="${err.message}"`,
      });
      res.end(JSON.stringify({ error: 'invalid_token', message: err.message }));
    } else {
      console.error('Token verification error:', err);
      sendJson(res, 500, { error: 'Internal server error' });
    }
  }
});

server.listen(CONFIG.port, () => {
  console.log(`OAuth 2.0 resource server listening on port ${CONFIG.port}`);
  console.log(`JWKS URI: ${CONFIG.jwksUri}`);
  console.log(`Expected issuer: ${CONFIG.issuer}`);
  console.log(`Expected audience: ${CONFIG.audience}`);
});