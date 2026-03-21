const express = require("express");
const jwt = require("jsonwebtoken");
const jwtAuthMiddleware = require("./jwtAuthMiddleware");
const { loginUser } = require("../userLogin");

const app = express();
app.use(express.json());

const JWT_SECRET = process.env.JWT_SECRET || "dev-secret-change-me";

app.post("/login", (req, res) => {
  const db = req.app.locals.db;
  const { username, password } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: "username and password are required" });
  }
  if (!db || typeof db.query !== "function") {
    return res.status(500).json({ error: "Legacy database connection is not configured" });
  }

  return loginUser(db, username, password, (err, user) => {
    if (err) {
      return res.status(500).json({ error: "Login failed" });
    }
    if (!user) {
      return res.status(401).json({ error: "Invalid username or password" });
    }

    const token = jwt.sign(
      { id: user.id, username: user.username, email: user.email, role: user.role || "user" },
      JWT_SECRET,
      { expiresIn: "1h" }
    );
    return res.json({ token });
  });
});

app.get("/me", jwtAuthMiddleware, (req, res) => {
  return res.json({ user: req.user });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Prototype API running on http://localhost:${port}`);
});
