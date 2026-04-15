function createJwtAuthMiddleware() {
  return function jwtAuthMiddleware(req, res, next) {
    const token = extractBearerToken(req.headers.authorization);
    if (!token) {
      return unauthorized(res);
    }