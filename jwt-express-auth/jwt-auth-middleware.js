'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');

const DEFAULT_SECRET = 'change-me-in-production';

function createJwtAuthMiddleware(options = {}) {
  const {
    secret = process.env.JWT_SECRET,
    publicKey = process.env.JWT_PUBLIC_KEY,
    algorithms = publicKey ? ['RS256', 'RS384', 'RS512'] : ['HS256'],
    issuer = process.env.JWT_ISSUER,
    audience = process.env.JWT_AUDIENCE,
    clockTolerance = 5,
    requestProperty = 'user',
  } = options;

  const key = publicKey || secret;
  if (!key) {
    throw new Error('JWT secret or public key is required');
  }

  const verifyOpts = {
    algorithms,
    clockTolerance,
  };
  if (issuer) verifyOpts.issuer = issuer;
  if (audience) verifyOpts.audience = audience;

  return function jwtAuthMiddleware(req, res, next) {
    const auth = req.headers.authorization;
    if (!auth || auth.length < 8) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }
    const prefix = auth.slice(0, 7);
    if (prefix.toLowerCase() !== 'bearer ') {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }
    const token = auth.slice(7).trim();
    if (!token) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }
    try {
      const payload = jwt.verify(token, key, verifyOpts);
      req[requestProperty] = {
        sub: payload.sub,
        id: payload.sub,
        email: payload.email,
        name: payload.name,
        roles: payload.roles || payload.role,
        ...payload,
      };
      next();
    } catch {
      res.status(401).json({ error: 'Unauthorized' });
    }
  };
}

module.exports = { createJwtAuthMiddleware };

if (require.main === module) {
  const app = express();
  const auth = createJwtAuthMiddleware({ secret: process.env.JWT_SECRET || DEFAULT_SECRET });
  app.get('/health', (_req, res) => {
    res.json({ ok: true });
  });
  app.get('/me', auth, (req, res) => {
    res.json({ user: req.user });
  });
  app.listen(Number(process.env.PORT) || 3000, () => {
    process.stdout.write(`listening on ${Number(process.env.PORT) || 3000}\n`);
  });
}
