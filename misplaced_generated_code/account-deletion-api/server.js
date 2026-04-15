'use strict';

const express = require('express');
const session = require('express-session');
const bcrypt = require('bcrypt');

const app = express();
app.use(express.json());

app.use(
  session({
    secret: process.env.SESSION_SECRET || 'change-me-in-production',
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    },
  })
);

const users = new Map();

function requireAuth(req, res, next) {
  if (!req.session || !req.session.userId) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  next();
}

async function getPasswordHashForUser(userId) {
  const row = users.get(userId);
  return row ? row.passwordHash : null;
}

async function removeUser(userId) {
  return users.delete(userId);
}

app.post('/delete-account', requireAuth, async (req, res) => {
  const password = req.body && req.body.password;
  if (typeof password !== 'string' || password.length === 0) {
    res.status(400).json({ error: 'Password required' });
    return;
  }

  const userId = req.session.userId;
  const passwordHash = await getPasswordHashForUser(userId);
  if (!passwordHash) {
    res.status(404).json({ error: 'User not found' });
    return;
  }

  let valid;
  try {
    valid = await bcrypt.compare(password, passwordHash);
  } catch {
    res.status(500).json({ error: 'Internal server error' });
    return;
  }

  if (!valid) {
    res.status(403).json({ error: 'Invalid password' });
    return;
  }

  await removeUser(userId);

  req.session.destroy((err) => {
    if (err) {
      res.status(500).json({ error: 'Account deleted but session cleanup failed' });
      return;
    }
    res.clearCookie('connect.sid', { path: '/' });
    res.status(204).send();
  });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stderr.write(`Listening on ${port}\n`);
});

module.exports = { app, users, requireAuth };
