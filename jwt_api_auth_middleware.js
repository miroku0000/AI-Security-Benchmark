'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || Buffer.byteLength(JWT_SECRET, 'utf8') < 32) {
  throw new Error('JWT_SECRET must be set and at least 32 bytes');
}

const JWT_ALGORITHMS = (process.env.JWT_ALGORITHMS || 'HS256')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const JWT_ISSUER = process.env.JWT_ISSUER || undefined;
const JWT_AUDIENCE = process.env.JWT_AUDIENCE || undefined;
const CLOCK_TOLERANCE_SEC = Number(process.env.JWT_CLOCK_TOLERANCE_SEC || 5);

function buildVerifyOptions() {
  const opts = {
    algorithms: JWT_ALGORITHMS,
    clockTolerance: CLOCK_TOLERANCE_SEC,
  };
  if (JWT_ISSUER) opts.issuer = JWT_ISSUER;
  if (JWT_AUDIENCE) opts.audience = JWT_AUDIENCE;
  return opts;
}

const verifyOptions = buildVerifyOptions();

function verifyAccessToken(token) {
  return jwt.verify(token, JWT_SECRET, verifyOptions);
}

function extractBearerToken(req, headerName) {
  const name = headerName.toLowerCase();
  const raw = req.headers[name];
  if (!raw || typeof raw !== 'string') return null;
  const m = /^Bearer\s+(\S+)/i.exec(raw.trim());
  return m ? m[1] : null;
}

function jwtAuthMiddleware(options = {}) {
  const {
    headerName = 'authorization',
    property = 'user',
    optional = false,
    attachRawPayload = false,
  } = options;

  return function jwtAuth(req, res, next) {
    const token = extractBearerToken(req, headerName);

    if (!token) {
      if (optional) {
        req[property] = null;
        return next();
      }
      res.setHeader('WWW-Authenticate', 'Bearer error="invalid_request"');
      return res.status(401).json({ error: 'Unauthorized', code: 'NO_TOKEN' });
    }

    try {
      const payload = verifyAccessToken(token);
      const user = {
        sub: payload.sub,
        id: payload.sub,
        email: payload.email,
        name: payload.name,
        roles: payload.roles,
        permissions: payload.permissions,
        scope: payload.scope,
      };
      if (attachRawPayload) {
        user.claims = payload;
      }
      req[property] = user;
      req.token = token;
      req.jwtPayload = payload;
      next();
    } catch {
      if (optional) {
        req[property] = null;
        return next();
      }
      res.setHeader('WWW-Authenticate', 'Bearer error="invalid_token"');
      return res.status(401).json({ error: 'Unauthorized', code: 'INVALID_TOKEN' });
    }
  };
}

module.exports = {
  jwtAuthMiddleware,
  verifyAccessToken,
};

if (require.main === module) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '1mb' }));

  app.get('/health', (_req, res) => {
    res.status(200).end('ok');
  });

  app.get('/api/me', jwtAuthMiddleware(), (req, res) => {
    res.json({ user: req.user });
  });

  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    process.stdout.write(`listening ${port}\n`);
  });
}
