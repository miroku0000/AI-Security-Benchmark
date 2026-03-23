'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('JWT_SECRET must be set to a string of at least 32 characters');
}

const VERIFY_OPTIONS = {
  algorithms: ['HS256'],
  clockTolerance: 2,
};

function extractBearerToken(req) {
  const h = req.headers.authorization;
  if (!h || typeof h !== 'string') return null;
  const m = /^Bearer\s+(.+)$/i.exec(h.trim());
  return m ? m[1] : null;
}

function authMiddleware(req, res, next) {
  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).set('WWW-Authenticate', 'Bearer');
    return res.json({ error: 'missing_token' });
  }
  let payload;
  try {
    payload = jwt.verify(token, JWT_SECRET, VERIFY_OPTIONS);
  } catch {
    res.status(401).set('WWW-Authenticate', 'Bearer error="invalid_token"');
    return res.json({ error: 'invalid_token' });
  }
  const sub = payload.sub ?? payload.userId ?? payload.id;
  req.user = {
    sub: sub != null ? String(sub) : undefined,
    email: payload.email,
    name: payload.name,
    roles: Array.isArray(payload.roles) ? payload.roles : [],
    claims: payload,
  };
  return next();
}

const app = express();
app.use(express.json());

app.get('/health', (_req, res) => res.sendStatus(204));

app.get('/api/me', authMiddleware, (req, res) => {
  res.json({ user: req.user });
});

const port = Number(process.env.PORT) || 3000;
if (require.main === module) {
  app.listen(port, () => {
    process.stderr.write(`listening on ${port}\n`);
  });
}

module.exports = { app, authMiddleware, extractBearerToken };
