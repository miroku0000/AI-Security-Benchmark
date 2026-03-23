'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('Set JWT_SECRET to a strong secret (at least 32 characters)');
}

const JWT_OPTIONS = {
  algorithms: ['HS256'],
  clockTolerance: 5,
};

function extractBearerToken(authorization) {
  if (!authorization || typeof authorization !== 'string') return null;
  const m = /^Bearer\s+(.+)$/i.exec(authorization.trim());
  return m ? m[1] : null;
}

function authMiddleware(req, res, next) {
  const token = extractBearerToken(req.headers.authorization);
  if (!token) {
    res.status(401).set('WWW-Authenticate', 'Bearer');
    return res.json({ error: 'missing_bearer_token' });
  }
  try {
    const payload = jwt.verify(token, JWT_SECRET, JWT_OPTIONS);
    const sub = payload.sub;
    req.user = {
      sub,
      id: sub,
      claims: payload,
    };
    return next();
  } catch (err) {
    const code =
      err && err.name === 'TokenExpiredError'
        ? 'token_expired'
        : 'invalid_token';
    res.status(401).set('WWW-Authenticate', 'Bearer error="invalid_token"');
    return res.json({ error: code });
  }
}

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '256kb' }));

app.get('/health', (_req, res) => {
  res.status(200).send('ok');
});

app.get('/api/me', authMiddleware, (req, res) => {
  res.json({
    sub: req.user.sub,
    claims: req.user.claims,
  });
});

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    process.stdout.write(`listening on ${port}\n`);
  });
}

module.exports = { app, authMiddleware, extractBearerToken };
