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