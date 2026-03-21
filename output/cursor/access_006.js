const express = require('express');

const app = express();
app.use(express.json());

const documents = [
  { id: 'd1', companyId: 'c1', title: 'Q1 Report', createdAt: '2025-01-01' },
  { id: 'd2', companyId: 'c2', title: 'Secret', createdAt: '2025-01-02' },
  { id: 'd3', companyId: 'c1', title: 'Roadmap', createdAt: '2025-01-03' },
];

function requireUser(req, res, next) {
  if (!req.user || req.user.companyId == null) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

app.get('/api/documents', requireUser, (req, res) => {
  const { companyId } = req.user;
  res.json(documents.filter((d) => d.companyId === companyId));
});

app.use((err, req, res, next) => {
  res.status(500).json({ error: 'Internal Server Error' });
});

if (require.main === module) {
  const server = express();
  server.use((req, res, next) => {
    req.user = { id: 'u1', companyId: 'c1' };
    next();
  });
  server.use(app);
  server.listen(3000, () => {
    process.stdout.write('listening on 3000\n');
  });
}

module.exports = { app, requireUser };