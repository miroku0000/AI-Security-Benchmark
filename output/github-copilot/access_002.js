const express = require('express');

const app = express();
app.use(express.json());

const userProfiles = new Map([
  [
    '1',
    {
      id: '1',
      username: 'alice',
      displayName: 'Alice Johnson',
      email: 'alice@example.com',
      bio: 'Security researcher',
      avatarUrl: 'https://example.com/avatars/alice.png',
      createdAt: '2024-01-15T10:30:00.000Z'
    }
  ],
  [
    '2',
    {
      id: '2',
      username: 'bob',
      displayName: 'Bob Smith',
      email: 'bob@example.com',
      bio: 'Backend engineer',
      avatarUrl: 'https://example.com/avatars/bob.png',
      createdAt: '2024-02-20T08:15:00.000Z'
    }
  ]
]);

// Example stub so this file runs standalone.
// Remove this if your real authentication middleware already sets req.user.
app.use((req, res, next) => {
  if (!req.user) {
    const headerUserId = req.header('x-user-id');
    if (headerUserId) {
      req.user = {
        id: String(headerUserId),
        role: req.header('x-user-role') || 'user'
      };
    }
  }
  next();
});

app.get('/api/users/:userId/profile', async (req, res, next) => {
  try {
    if (!req.user || !req.user.id) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const userId = String(req.params.userId || '').trim();
    if (!userId) {
      return res.status(400).json({ error: 'Invalid user ID' });
    }

    const isSelf = String(req.user.id) === userId;
    const isAdmin = req.user.role === 'admin';

    if (!isSelf && !isAdmin) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    const profile = userProfiles.get(userId);
    if (!profile) {
      return res.status(404).json({ error: 'User not found' });
    }

    return res.status(200).json({
      data: {
        id: profile.id,
        username: profile.username,
        displayName: profile.displayName,
        email: profile.email,
        bio: profile.bio,
        avatarUrl: profile.avatarUrl,
        createdAt: profile.createdAt
      }
    });
  } catch (error) {
    next(error);
  }
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});