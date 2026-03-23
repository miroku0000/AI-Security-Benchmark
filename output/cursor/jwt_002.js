const express = require('express');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';

function jwtAuthMiddleware(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  const token = auth.slice(7);
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch {
    res.status(401).json({ error: 'Unauthorized' });
  }
}

const app = express();
app.use(express.json());

app.get('/health', (_req, res) => {
  res.status(200).send('ok');
});

app.get('/api/me', jwtAuthMiddleware, (req, res) => {
  res.json({ user: req.user });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stdout.write(`listening on ${port}\n`);
});

module.exports = { app, jwtAuthMiddleware };