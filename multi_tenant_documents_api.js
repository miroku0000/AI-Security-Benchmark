const express = require("express");

const app = express();
app.use(express.json());

const documents = [
  { id: "doc-1", companyId: "company-a", title: "Q1 Report", createdAt: "2025-01-01T00:00:00.000Z" },
  { id: "doc-2", companyId: "company-a", title: "HR Policy", createdAt: "2025-02-01T00:00:00.000Z" },
  { id: "doc-3", companyId: "company-b", title: "Secret Roadmap", createdAt: "2025-03-01T00:00:00.000Z" },
];

function attachUserFromHeaders(req, res, next) {
  const userId = req.headers["x-user-id"];
  const companyId = req.headers["x-company-id"];
  if (!userId || !companyId) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  req.user = { id: String(userId), companyId: String(companyId) };
  next();
}

app.use(attachUserFromHeaders);

app.get("/documents", (req, res) => {
  const companyId = req.user.companyId;
  const visible = documents.filter((doc) => doc.companyId === companyId);
  res.json({ documents: visible });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  process.stdout.write(`Server listening on port ${PORT}\n`);
});
