const express = require('express');

const app = express();

app.use(express.json());

const usersById = new Map([
  ['1', { id: '1', username: 'alice', displayName: 'Alice', email: 'alice@example.com', createdAt: '2024-01-10T12:00:00.000Z' }],
  ['2', { id: '2', username: 'bob', displayName: 'Bob', email: 'bob@example.com', createdAt: '2024-02-15T09:30:00.000Z' }],
]);

function requireAuth(req, res, next) {
  if (!req.user || !req.user.id) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

app.get('/users/:userId', requireAuth, (req, res) => {
  const { userId } = req.params;
  const authed = req.user;

  if (authed.id !== userId && authed.role !== 'admin') {
    return res.status(403).json({ error: 'Forbidden' });
  }

  const profile = usersById.get(userId);
  if (!profile) {
    return res.status(404).json({ error: 'User not found' });
  }

  return res.json({ profile });
});

app.listen(process.env.PORT || 3000, () => {
  console.log(`Listening on ${process.env.PORT || 3000}`);
});