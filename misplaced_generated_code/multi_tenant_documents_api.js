const express = require("express");

const documents = [
  { id: "1", companyId: "c1", title: "Q1 Report" },
  { id: "2", companyId: "c1", title: "Roadmap" },
  { id: "3", companyId: "c2", title: "Secret" },
];

const router = express.Router();

router.get("/", (req, res) => {
  const { companyId } = req.user;
  const list = documents.filter((d) => d.companyId === companyId);
  res.json(list);
});

router.get("/:id", (req, res) => {
  const { companyId } = req.user;
  const doc = documents.find(
    (d) => d.id === req.params.id && d.companyId === companyId
  );
  if (!doc) {
    return res.status(404).json({ error: "Not found" });
  }
  res.json(doc);
});

if (require.main === module) {
  const app = express();
  app.use(express.json());
  app.use((req, res, next) => {
    req.user = { id: "u1", companyId: "c1" };
    next();
  });
  app.use("/documents", router);
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    process.stdout.write(`listening on ${port}\n`);
  });
}

module.exports = { router, documents };
