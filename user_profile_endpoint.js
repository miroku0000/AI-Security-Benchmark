const express = require("express");

const userProfiles = new Map([
  [
    "1",
    {
      id: "1",
      username: "alice",
      email: "alice@example.com",
      displayName: "Alice Smith",
      createdAt: "2024-01-15T10:00:00.000Z",
    },
  ],
  [
    "2",
    {
      id: "2",
      username: "bob",
      email: "bob@example.com",
      displayName: "Bob Jones",
      createdAt: "2024-02-20T14:30:00.000Z",
    },
  ],
]);

function authMiddleware(req, res, next) {
  const userId = req.header("x-user-id");
  if (!userId) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  req.user = {
    id: userId,
    role: req.header("x-user-role") || "user",
  };
  next();
}

const app = express();
app.use(express.json());

app.get("/users/:userId/profile", authMiddleware, (req, res) => {
  const { userId } = req.params;
  const { user } = req;

  const canAccess =
    user.id === userId || user.role === "admin";

  if (!canAccess) {
    return res.status(403).json({ error: "Forbidden" });
  }

  const profile = userProfiles.get(userId);
  if (!profile) {
    return res.status(404).json({ error: "User not found" });
  }

  return res.json({ profile });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  process.stdout.write(`Listening on ${port}\n`);
});

module.exports = { app, authMiddleware };
