const express = require('express');

const app = express();
app.use(express.json());

const documents = [
  { id: 'doc-1', companyId: 'company-1', title: 'Q1 Financial Report', content: 'Revenue grew 18%.' },
  { id: 'doc-2', companyId: 'company-1', title: 'HR Handbook', content: 'Welcome to the team.' },
  { id: 'doc-3', companyId: 'company-2', title: 'Product Roadmap', content: 'New launch scheduled for July.' }
];

function mockAuth(req, res, next) {
  const id = req.header('x-user-id');
  const companyId = req.header('x-company-id');

  if (!id || !companyId) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  req.user = { id, companyId };
  next();
}

function requireAuth(req, res, next) {
  if (!req.user || !req.user.id || !req.user.companyId) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  next();
}

app.use(mockAuth);

app.get('/api/documents/:id', requireAuth, (req, res) => {
  const document = documents.find(
    (doc) => doc.id === req.params.id && doc.companyId === req.user.companyId
  );

  if (!document) {
    return res.status(404).json({ error: 'Document not found' });
  }

  res.json({
    id: document.id,
    title: document.title,
    content: document.content
  });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});