const jwt = require("jsonwebtoken");

function jwtVerifyMiddleware(secret) {
  return function jwtVerify(req, res, next) {
    const header = req.headers.authorization;
    if (!header || typeof header !== "string") {
      res.status(401).json({ error: "Authorization header required" });
      return;
    }
    const parts = header.split(" ");
    const token = parts.length === 2 && /^Bearer$/i.test(parts[0]) ? parts[1] : null;
    if (!token) {
      res.status(401).json({ error: "Expected Bearer token" });
      return;
    }
    try {
      const payload = jwt.verify(token, secret);
      req.user = payload;
      next();
    } catch {
      res.status(401).json({ error: "Invalid or expired token" });
    }
  };
}

module.exports = { jwtVerifyMiddleware };
