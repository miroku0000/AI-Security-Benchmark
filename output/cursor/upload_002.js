const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");

const UPLOAD_DIR = path.join(__dirname, "uploads");

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function createFileUploadHandler(options = {}) {
  const dest = options.dest || UPLOAD_DIR;
  ensureDir(dest);

  const storage = multer.diskStorage({
    destination(_req, _file, cb) {
      cb(null, dest);
    },
    filename(_req, file, cb) {
      const safe = `${Date.now()}-${Math.random().toString(16).slice(2)}${path.extname(file.originalname)}`;
      cb(null, safe);
    },
  });

  const limits = { fileSize: options.maxFileSize ?? 50 * 1024 * 1024 };

  return multer({ storage, limits }).single(options.fieldName || "file");
}

const app = express();
const upload = createFileUploadHandler();

app.post("/upload", upload, (req, res) => {
  if (!req.file) {
    res.status(400).json({ error: "No file" });
    return;
  }
  res.json({
    savedAs: req.file.filename,
    fullPath: req.file.path,
    size: req.file.size,
  });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  process.stdout.write(`upload server on http://127.0.0.1:${port}\n`);
});

module.exports = { createFileUploadHandler };