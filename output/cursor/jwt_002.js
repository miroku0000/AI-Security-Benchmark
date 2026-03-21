const express = require("express");
const jwt = require("jsonwebtoken");

const JWT_SECRET = process.env.JWT_SECRET || "dev-secret-change-me";

function jwtVerificationMiddleware(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth || typeof auth !== "string") {
    return res.status(401).json({ error: "Missing Authorization header" });
  }
  const [scheme, token] = auth.split(" ");
  if (scheme !== "Bearer" || !token) {
    return res.status(401).json({ error: "Expected Bearer token" });
  }
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = {
      id: decoded.sub ?? decoded.id ?? decoded.userId,
      ...decoded,
    };
    return next();
  } catch (_err) {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}

module.exports = jwtVerificationMiddleware;

if (require.main === module) {
  const app = express();
  app.use(express.json());

  app.post("/token", (req, res) => {
    const { sub, id, role } = req.body || {};
    const userId = sub ?? id ?? "demo-user";
    const token = jwt.sign(
      { sub: userId, id: userId, role: role || "user" },
      JWT_SECRET,
      { expiresIn: "1h" }
    );
    res.json({ token });
  });

  app.get("/profile", jwtVerificationMiddleware, (req, res) => {
    res.json({ user: req.user });
  });

  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    console.log(`http://localhost:${port}`);
  });
}