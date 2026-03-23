const express = require('express');

const app = express();
app.use(express.json());

const profilesByUserId = {
  '1': { id: '1', username: 'alice', email: 'alice@example.com', displayName: 'Alice', createdAt: '2024-01-15T00:00:00.000Z' },
  '2': { id: '2', username: 'bob', email: 'bob@example.com', displayName: 'Bob', createdAt: '2024-02-20T00:00:00.000Z' },
};

function authMiddleware(req, res, next) {
  req.user = { id: '1', roles: ['user'] };
  next();
}

app.use(authMiddleware);

app.get('/users/:userId/profile', (req, res) => {
  const { userId } = req.params;
  const authedId = req.user && String(req.user.id);

  if (!authedId) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  if (authedId !== String(userId)) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  const profile = profilesByUserId[userId];
  if (!profile) {
    return res.status(404).json({ error: 'User not found' });
  }

  return res.status(200).json({ profile });
});

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => {});
}

module.exports = { app };
