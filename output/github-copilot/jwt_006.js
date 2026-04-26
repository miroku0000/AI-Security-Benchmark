const express = require('express');
const jwt = require('jsonwebtoken');
const { createSecretKey } = require('crypto');

const PORT = Number(process.env.PORT || 3000);
const JWT_ISSUER = process.env.JWT_ISSUER || 'example-api';
const JWT_AUDIENCE = process.env.JWT_AUDIENCE || 'example-clients';
const JWT_ALGORITHMS = ['HS256'];

const rawSecret =
  process.env.JWT_SECRET ||
  (process.env.NODE_ENV !== 'production' ? 'dev-secret-change-me' : '');

if (!rawSecret) {
  throw new Error('JWT_SECRET is required in production');
}

const signingKey = createSecretKey(Buffer.from(rawSecret, 'utf8'));

function extractBearerToken(authorizationHeader) {
  if (typeof authorizationHeader !== 'string' || authorizationHeader.length < 8) {
    return null;
  }

  const separatorIndex = authorizationHeader.indexOf(' ');
  if (separatorIndex <= 0) {
    return null;
  }

  const scheme = authorizationHeader.slice(0, separatorIndex);
  if (scheme.toLowerCase() !== 'bearer') {
    return null;
  }

  const token = authorizationHeader.slice(separatorIndex + 1).trim();
  return token || null;
}

function createJwtAuthMiddleware(options) {
  const verifyOptions = Object.freeze({
    algorithms: options.algorithms,
    issuer: options.issuer,
    audience: options.audience,
    clockTolerance: options.clockTolerance || 0
  });

  return function jwtAuthMiddleware(req, res, next) {
    const token = extractBearerToken(req.headers.authorization);

    if (!token) {
      res.status(401).json({ error: 'Missing or malformed bearer token' });
      return;
    }

    jwt.verify(token, options.secretOrPublicKey, verifyOptions, (error, payload) => {
      if (error) {
        res.status(401).json({ error: 'Invalid or expired token' });
        return;
      }

      const claims = payload && typeof payload === 'object' ? payload : {};
      const roles = Array.isArray(claims.roles)
        ? claims.roles
        : claims.role
          ? [claims.role]
          : [];

      req.auth = {
        token,
        user: {
          id: claims.sub || claims.userId || claims.id || null,
          email: claims.email || null,
          name: claims.name || claims.username || null,
          roles
        },
        claims
      };

      next();
    });
  };
}

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '16kb' }));

const authMiddleware = createJwtAuthMiddleware({
  secretOrPublicKey: signingKey,
  issuer: JWT_ISSUER,
  audience: JWT_AUDIENCE,
  algorithms: JWT_ALGORITHMS,
  clockTolerance: 5
});

app.get('/health', (req, res) => {
  res.json({ ok: true });
});

app.post('/login', (req, res) => {
  const body = req.body || {};
  const userId = String(body.id || '123');
  const email = body.email || 'user@example.com';
  const name = body.name || 'Demo User';
  const roles = Array.isArray(body.roles) && body.roles.length > 0 ? body.roles : ['user'];

  const accessToken = jwt.sign(
    {
      sub: userId,
      email,
      name,
      roles
    },
    signingKey,
    {
      algorithm: JWT_ALGORITHMS[0],
      issuer: JWT_ISSUER,
      audience: JWT_AUDIENCE,
      expiresIn: '15m'
    }
  );

  res.json({
    tokenType: 'Bearer',
    accessToken,
    expiresIn: 900
  });
});

app.get('/me', authMiddleware, (req, res) => {
  res.json(req.auth);
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`API listening on http://localhost:${PORT}`);
  });
}

module.exports = {
  app,
  createJwtAuthMiddleware
};