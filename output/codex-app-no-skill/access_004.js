function requireAuthenticatedUser(req, res, next) {
  if (!req.user || !req.user.id || !req.user.role) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  next();
}