const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';

function jwtAuthMiddleware(req, res, next) {
  const header = req.headers.authorization;
  if (!header || typeof header !== 'string' || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const token = header.slice(7).trim();
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    next();
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

const app = express();
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ ok: true });
});

app.get('/api/me', jwtAuthMiddleware, (req, res) => {
  res.json({ user: req.user });
});

const port = Number(process.env.PORT) || 3000;
if (require.main === module) {
  app.listen(port, () => {
    console.log(`Listening on ${port}`);
  });
}

module.exports = { app, jwtAuthMiddleware, JWT_SECRET };
