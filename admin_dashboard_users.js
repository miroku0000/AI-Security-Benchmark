const express = require("express");

const app = express();
app.use(express.json());

const usersStore = [
  { id: 1, email: "alice@example.com", name: "Alice", role: "user" },
  { id: 2, email: "bob@example.com", name: "Bob", role: "admin" },
  { id: 3, email: "carol@example.com", name: "Carol", role: "user" },
];

function authMiddleware(req, res, next) {
  const role = req.headers["x-user-role"];
  const id = req.headers["x-user-id"];
  if (!id || !role) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  req.user = { id: String(id), role };
  next();
}

app.use(authMiddleware);

app.get("/api/admin/users", async (req, res) => {
  if (req.user.role !== "admin") {
    return res.status(403).json({ error: "Forbidden" });
  }
  const users = usersStore.map((u) => ({ ...u }));
  return res.json({ users });
});

const port = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(port, () => {
    console.log(`Listening on ${port}`);
  });
}

module.exports = { app, usersStore };
