'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('Set JWT_SECRET to a strong secret (at least 32 characters)');
}

const BEARER_PREFIX = /^Bearer\s+/i;

const jwtAuthMiddleware = (options = {}) => {
  const algorithms = options.algorithms || ['HS256'];
  const issuer = options.issuer;
  const audience = options.audience;
  const clockTolerance = options.clockTolerance ?? 0;
  const userProperty = options.userProperty || 'user';

  const verifyOpts = { algorithms, clockTolerance };
  if (issuer !== undefined) verifyOpts.issuer = issuer;
  if (audience !== undefined) verifyOpts.audience = audience;

  return function authMiddleware(req, res, next) {
    const header = req.headers.authorization;
    if (!header || typeof header !== 'string') {
      res.status(401).set('WWW-Authenticate', 'Bearer').json({ error: 'Unauthorized' });
      return;
    }
    const match = header.match(BEARER_PREFIX);
    if (!match) {
      res.status(401).set('WWW-Authenticate', 'Bearer').json({ error: 'Unauthorized' });
      return;
    }
    const token = header.slice(match[0].length).trim();
    if (!token) {
      res.status(401).set('WWW-Authenticate', 'Bearer').json({ error: 'Unauthorized' });
      return;
    }
    try {
      const payload = jwt.verify(token, JWT_SECRET, verifyOpts);
      req[userProperty] = payload;
      next();
    } catch {
      res.status(401).set('WWW-Authenticate', 'Bearer').json({ error: 'Unauthorized' });
    }
  };
};

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));

app.get('/health', (_req, res) => {
  res.status(200).json({ ok: true });
});

app.get('/api/me', jwtAuthMiddleware(), (req, res) => {
  const sub = req.user && req.user.sub;
  const email = req.user && req.user.email;
  res.json({ sub, email, claims: req.user });
});

const port = Number(process.env.PORT) || 3000;
if (require.main === module) {
  app.listen(port, () => {
    process.stderr.write(`listening on ${port}\n`);
  });
}

module.exports = { app, jwtAuthMiddleware };
