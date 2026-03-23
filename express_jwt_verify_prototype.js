const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';

function jwtVerifyMiddleware(options = {}) {
  const { optional = false } = options;
  return (req, res, next) => {
    const header = req.headers.authorization;
    let token = null;
    if (header && header.startsWith('Bearer ')) {
      token = header.slice(7);
    }
    if (!token) {
      if (optional) {
        req.user = null;
        return next();
      }
      return res.status(401).json({ error: 'Missing or invalid Authorization header' });
    }
    try {
      const payload = jwt.verify(token, JWT_SECRET);
      req.user = {
        sub: payload.sub,
        email: payload.email,
        role: payload.role,
        ...payload,
      };
      return next();
    } catch (err) {
      if (optional) {
        req.user = null;
        return next();
      }
      return res.status(401).json({ error: 'Invalid or expired token' });
    }
  };
}

const app = express();
app.use(express.json());

app.get('/health', (req, res) => res.json({ ok: true }));

app.get('/api/me', jwtVerifyMiddleware(), (req, res) => {
  res.json({ user: req.user });
});

app.get('/api/public', jwtVerifyMiddleware({ optional: true }), (req, res) => {
  res.json({ authenticated: !!req.user, user: req.user });
});

const port = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(port, () => {
    console.log(`Listening on ${port}`);
  });
}

module.exports = { app, jwtVerifyMiddleware };
