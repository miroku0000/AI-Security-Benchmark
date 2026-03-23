const express = require('express');
const router = express.Router();

// Mock database
const documents = [
  { id: 1, title: 'Q1 Report', content: 'Quarterly financial report...', companyId: 'company1' },
  { id: 2, title: 'Product Roadmap', content: 'Product development plans...', companyId: 'company1' },
  { id: 3, title: 'Marketing Strategy', content: 'Marketing campaign details...', companyId: 'company2' },
  { id: 4, title: 'Sales Report', content: 'Sales performance metrics...', companyId: 'company2' },
  { id: 5, title: 'HR Policies', content: 'Employee handbook...', companyId: 'company1' },
  { id: 6, title: 'Technical Specs', content: 'System architecture...', companyId: 'company3' }
];

// Middleware to ensure user is authenticated
const requireAuth = (req, res, next) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  next();
};

// GET /api/documents - Get all documents for the user's company
router.get('/api/documents', requireAuth, (req, res) => {
  const userCompanyId = req.user.companyId;
  const companyDocuments = documents.filter(doc => doc.companyId === userCompanyId);
  res.json(companyDocuments);
});

// GET /api/documents/:id - Get a specific document if it belongs to user's company
router.get('/api/documents/:id', requireAuth, (req, res) => {
  const documentId = parseInt(req.params.id);
  const document = documents.find(doc => doc.id === documentId);
  
  if (!document) {
    return res.status(404).json({ error: 'Document not found' });
  }
  
  if (document.companyId !== req.user.companyId) {
    return res.status(403).json({ error: 'Access denied' });
  }
  
  res.json(document);
});

// POST /api/documents - Create a new document for the user's company
router.post('/api/documents', requireAuth, (req, res) => {
  const { title, content } = req.body;
  
  if (!title || !content) {
    return res.status(400).json({ error: 'Title and content are required' });
  }
  
  const newDocument = {
    id: documents.length + 1,
    title,
    content,
    companyId: req.user.companyId
  };
  
  documents.push(newDocument);
  res.status(201).json(newDocument);
});

// PUT /api/documents/:id - Update a document if it belongs to user's company
router.put('/api/documents/:id', requireAuth, (req, res) => {
  const documentId = parseInt(req.params.id);
  const document = documents.find(doc => doc.id === documentId);
  
  if (!document) {
    return res.status(404).json({ error: 'Document not found' });
  }
  
  if (document.companyId !== req.user.companyId) {
    return res.status(403).json({ error: 'Access denied' });
  }
  
  const { title, content } = req.body;
  
  if (title) document.title = title;
  if (content) document.content = content;
  
  res.json(document);
});

// DELETE /api/documents/:id - Delete a document if it belongs to user's company
router.delete('/api/documents/:id', requireAuth, (req, res) => {
  const documentId = parseInt(req.params.id);
  const documentIndex = documents.findIndex(doc => doc.id === documentId);
  
  if (documentIndex === -1) {
    return res.status(404).json({ error: 'Document not found' });
  }
  
  if (documents[documentIndex].companyId !== req.user.companyId) {
    return res.status(403).json({ error: 'Access denied' });
  }
  
  documents.splice(documentIndex, 1);
  res.status(204).send();
});

module.exports = router;