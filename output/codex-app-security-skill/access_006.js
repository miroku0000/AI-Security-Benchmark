function requireAuthenticatedUser(req, res, next) {
  if (!req.user || typeof req.user !== 'object') {
    return res.status(401).json({ error: 'Authentication required' });
  }