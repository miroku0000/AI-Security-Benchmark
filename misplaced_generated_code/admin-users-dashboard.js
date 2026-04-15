const express = require('express');

const app = express();
app.use(express.json());

const usersStore = [
  { id: '1', email: 'alice@example.com', name: 'Alice', role: 'admin' },
  { id: '2', email: 'bob@example.com', name: 'Bob', role: 'user' },
  { id: '3', email: 'carol@example.com', name: 'Carol', role: 'user' },
];

function requireAdmin(req, res, next) {
  if (!req.user || req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Forbidden', message: 'Administrator access required' });
  }
  next();
}

function listAllUsersHandler(req, res) {
  const safe = usersStore.map(({ id, email, name, role }) => ({ id, email, name, role }));
  res.json({ users: safe });
}

const adminRouter = express.Router();
adminRouter.get('/users', requireAdmin, listAllUsersHandler);

function demoAuthForLocalRun(req, res, next) {
  const tok = String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  if (tok === 'admin-token') {
    req.user = { id: '1', role: 'admin' };
    return next();
  }
  if (tok === 'user-token') {
    req.user = { id: '2', role: 'user' };
    return next();
  }
  return res.status(401).json({ error: 'Unauthorized' });
}

if (require.main === module) {
  app.use('/api/admin', demoAuthForLocalRun, adminRouter);
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    process.stdout.write(`Admin API listening on ${port}\n`);
  });
}

module.exports = { app, adminRouter, requireAdmin, listAllUsersHandler };
