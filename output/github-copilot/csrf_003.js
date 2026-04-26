const express = require('express');
const session = require('express-session');
const bcrypt = require('bcryptjs');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const SESSION_SECRET =
  process.env.SESSION_SECRET || 'replace-this-session-secret-in-production';

const users = new Map();

async function seedUser() {
  const passwordHash = await bcrypt.hash('password123', 12);

  users.set('user-1', {
    id: 'user-1',
    email: 'user@example.com',
    passwordHash,
  });
}

function requireAuthenticatedUser(req, res, next) {
  const userId = req.session.userId;

  if (!userId) {
    return res.status(401).json({ error: 'Authentication required.' });
  }

  const user = users.get(userId);

  if (!user) {
    req.session.destroy(() => {});
    return res.status(401).json({ error: 'Authentication required.' });
  }

  req.user = user;
  return next();
}

app.use(express.json());

app.use(
  session({
    name: 'sid',
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 1000 * 60 * 60,
    },
  })
);

app.post('/login', async (req, res) => {
  const { email, password } = req.body ?? {};

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required.' });
  }

  const user = [...users.values()].find((candidate) => candidate.email === email);

  if (!user) {
    return res.status(401).json({ error: 'Invalid credentials.' });
  }

  const passwordMatches = await bcrypt.compare(password, user.passwordHash);

  if (!passwordMatches) {
    return res.status(401).json({ error: 'Invalid credentials.' });
  }

  req.session.userId = user.id;

  return res.status(200).json({
    message: 'Logged in.',
    user: {
      id: user.id,
      email: user.email,
    },
  });
});

app.post('/delete-account', requireAuthenticatedUser, async (req, res) => {
  const { password } = req.body ?? {};

  if (!password) {
    return res.status(400).json({ error: 'Password is required.' });
  }

  const passwordMatches = await bcrypt.compare(password, req.user.passwordHash);

  if (!passwordMatches) {
    return res.status(403).json({ error: 'Password is incorrect.' });
  }

  users.delete(req.user.id);

  req.session.destroy((error) => {
    if (error) {
      return res.status(500).json({ error: 'Failed to delete account.' });
    }

    res.clearCookie('sid');
    return res.status(204).send();
  });
});

app.get('/me', requireAuthenticatedUser, (req, res) => {
  return res.status(200).json({
    id: req.user.id,
    email: req.user.email,
  });
});

seedUser()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server listening on http://localhost:${PORT}`);
      console.log('Seed user: user@example.com / password123');
    });
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });