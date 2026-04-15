function requireAuthenticatedUser(req, res, next) {
  if (!req.user || typeof req.user !== 'object' || req.user === null) {
    return res.status(401).json({
      error: 'authentication_required'
    });
  }