const express = require("express");

const app = express();
app.use(express.json());

if (require.main === module) {
  app.use((req, _res, next) => {
    req.user = { id: "demo-user", companyId: "acme" };
    next();
  });
}

const documents = [
  { id: "1", companyId: "acme", title: "Acme Q1", content: "..." },
  { id: "2", companyId: "acme", title: "Acme HR", content: "..." },
  { id: "3", companyId: "otherco", title: "OtherCo Secret", content: "..." },
];

function requireAuthenticatedUser(req, res, next) {
  if (!req.user || req.user.companyId == null) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

app.get("/api/documents", requireAuthenticatedUser, (req, res) => {
  const { companyId } = req.user;
  const list = documents.filter((d) => d.companyId === companyId);
  res.json(list);
});

app.get("/api/documents/:id", requireAuthenticatedUser, (req, res) => {
  const { companyId } = req.user;
  const doc = documents.find(
    (d) => d.id === req.params.id && d.companyId === companyId
  );
  if (!doc) {
    return res.status(404).json({ error: "Not found" });
  }
  res.json(doc);
});

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => {});
}

module.exports = { app, requireAuthenticatedUser };
