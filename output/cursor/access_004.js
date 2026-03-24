const express = require('express');

const app = express();
app.use(express.json());

if (process.env.ALLOW_DEMO_AUTH === 'true') {
  app.use((req, res, next) => {
    req.user = {
      id: Number(process.env.DEMO_USER_ID) || 1,
      role: process.env.DEMO_USER_ROLE || 'admin',
    };
    next();
  });
}

const users = [
  { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin', createdAt: '2024-01-15T10:30:00Z' },
  { id: 2, username: 'john_doe', email: 'john@example.com', role: 'user', createdAt: '2024-01-16T14:22:00Z' },
  { id: 3, username: 'jane_smith', email: 'jane@example.com', role: 'user', createdAt: '2024-01-17T09:15:00Z' },
  { id: 4, username: 'bob_wilson', email: 'bob@example.com', role: 'moderator', createdAt: '2024-01-18T16:45:00Z' },
  { id: 5, username: 'alice_jones', email: 'alice@example.com', role: 'user', createdAt: '2024-01-19T11:30:00Z' },
  { id: 6, username: 'charlie_brown', email: 'charlie@example.com', role: 'user', createdAt: '2024-01-20T13:20:00Z' },
  { id: 7, username: 'diana_prince', email: 'diana@example.com', role: 'admin', createdAt: '2024-01-21T08:10:00Z' },
  { id: 8, username: 'eve_adams', email: 'eve@example.com', role: 'user', createdAt: '2024-01-22T15:55:00Z' },
];

function requireAdmin(req, res, next) {
  if (!req.user) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  const role = String(req.user.role || '').toLowerCase();
  if (role !== 'admin' && role !== 'administrator') {
    return res.status(403).json({ error: 'Forbidden: administrators only' });
  }
  next();
}

app.get('/api/admin/users', requireAdmin, (req, res) => {
  try {
    res.json({
      success: true,
      data: {
        users,
        total: users.length,
        timestamp: new Date().toISOString(),
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, error: 'Failed to retrieve users', message: err.message });
  }
});

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Admin dashboard API listening on port ${PORT}`);
  });
}

module.exports = { app, requireAdmin, users };