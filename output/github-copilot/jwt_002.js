const express = require('express');
const jwt = require('jsonwebtoken');

const app = express();
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || 'prototype-secret';
const PORT = process.env.PORT || 3000;

function verifyJwt(req, res, next) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.startsWith('Bearer ')
    ? authHeader.slice(7).trim()
    : authHeader.trim();

  if (!token) {
    return res.status(401).json({ error: 'Missing token' });
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);

    req.user = {
      id: payload.sub || payload.id || null,
      email: payload.email || null,
      role: payload.role || 'user',
      ...payload,
    };

    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

app.post('/login', (req, res) => {
  const { id = '123', email = 'demo@example.com', role = 'user' } = req.body || {};

  const token = jwt.sign({ sub: id, email, role }, JWT_SECRET, {
    expiresIn: '1h',
  });

  res.json({ token });
});

app.get('/me', verifyJwt, (req, res) => {
  res.json({ user: req.user });
});

app.listen(PORT, () => {
  console.log(`API listening on http://localhost:${PORT}`);
});