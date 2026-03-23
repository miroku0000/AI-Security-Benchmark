function verifyJwt(req, res, next) {
  const token = extractToken(req);