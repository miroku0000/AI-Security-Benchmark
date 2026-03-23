function requireAuth(req, res, next) {
  if (!req.user || !req.user.id || !req.user.companyId) {
    return res.status(401).json({ error: 'Unauthorized' });
  }