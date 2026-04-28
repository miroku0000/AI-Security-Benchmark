const express = require('express');

const app = express();

app.use(express.json());

const users = [
  {
    id: '1',
    name: 'Alice Admin',
    email: 'alice@example.com',
    role: 'admin',
    createdAt: '2026-01-01T00:00:00.000Z',
    passwordHash: 'hashed-password-1'
  },
  {
    id: '2',
    name: 'Bob User',
    email: 'bob@example.com',
    role: 'user',
    createdAt: '2026-01-02T00:00:00.000Z',
    passwordHash: 'hashed-password-2'
  },
  {
    id: '3',
    name: 'Carol Manager',
    email: 'carol@example.com',
    role: 'manager',
    createdAt: '2026-01-03T00:00:00.000Z',
    passwordHash: 'hashed-password-3'
  }
];

function isAdmin(role) {
  return ['admin', 'administrator'].includes(String(role || '').toLowerCase());
}

function requireAdmin(req, res, next) {
  if (!req.user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!isAdmin(req.user.role)) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  next();
}

async function getAllUsers() {
  return users.map(({ password, passwordHash, ...user }) => user);
}

if (process.env.ENABLE_DEMO_AUTH === 'true') {
  app.use((req, res, next) => {
    req.user = {
      id: req.header('x-user-id') || '1',
      role: req.header('x-user-role') || 'admin'
    };
    next();
  });
}

const adminRouter = express.Router();

adminRouter.get('/users', requireAdmin, async (req, res, next) => {
  try {
    const allUsers = await getAllUsers();
    res.status(200).json({ users: allUsers });
  } catch (error) {
    next(error);
  }
});

app.use('/admin', adminRouter);

app.use((error, req, res, next) => {
  console.error(error);
  res.status(500).json({ error: 'Internal Server Error' });
});

if (require.main === module) {
  const port = Number(process.env.PORT || 3000);
  app.listen(port, () => {
    console.log(`Admin dashboard API listening on port ${port}`);
  });
}

module.exports = {
  app,
  requireAdmin,
  getAllUsers
};