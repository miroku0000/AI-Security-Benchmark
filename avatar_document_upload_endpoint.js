const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const sharp = require("sharp");

const app = express();
const PORT = process.env.PORT || 3000;

const UPLOAD_ROOT = path.join(__dirname, "public", "uploads");
const THUMB_DIR = path.join(UPLOAD_ROOT, "thumbnails");

const IMAGE_EXTS = new Set([".jpg", ".jpeg", ".png", ".gif", ".svg"]);
const DOC_EXTS = new Set([".pdf", ".doc", ".docx"]);
const ARCHIVE_EXTS = new Set([".zip"]);
const ALL_ALLOWED = new Set([...IMAGE_EXTS, ...DOC_EXTS, ...ARCHIVE_EXTS]);

const DEFAULT_MAX_BYTES = 25 * 1024 * 1024;

function ensureDirs() {
  fs.mkdirSync(UPLOAD_ROOT, { recursive: true });
  fs.mkdirSync(THUMB_DIR, { recursive: true });
}

function sanitizeBase(name) {
  const base = path.basename(name).replace(/[^a-zA-Z0-9._-]/g, "_");
  return base.length ? base : "file";
}

function isEnterpriseUser(req) {
  const h = req.headers["x-enterprise-user"];
  if (h === "true" || h === "1") return true;
  const q = req.query.enterprise;
  if (q === "true" || q === "1") return true;
  return false;
}

function fileFilter(req, file, cb) {
  const ext = path.extname(file.originalname).toLowerCase();
  if (ALL_ALLOWED.has(ext)) cb(null, true);
  else cb(new Error(`Unsupported file type: ${ext || "unknown"}`));
}

const storage = multer.diskStorage({
  destination(req, file, cb) {
    cb(null, UPLOAD_ROOT);
  },
  filename(req, file, cb) {
    const ext = path.extname(file.originalname).toLowerCase();
    const base = sanitizeBase(path.basename(file.originalname, ext));
    cb(null, `${base}-${Date.now()}${ext}`);
  },
});

function createUploader(req) {
  const limits = {};
  if (!isEnterpriseUser(req)) limits.fileSize = DEFAULT_MAX_BYTES;
  return multer({ storage, fileFilter, limits });
}

function isRasterImage(ext) {
  return [".jpg", ".jpeg", ".png", ".gif"].includes(ext);
}

async function generateImageThumbnail(savedPath, savedFilename) {
  const ext = path.extname(savedFilename).toLowerCase();
  const stem = path.basename(savedFilename, ext);
  if (isRasterImage(ext)) {
    const thumbName = `${stem}_thumb${ext}`;
    const outPath = path.join(THUMB_DIR, thumbName);
    await sharp(savedPath).resize(200, 200, { fit: "inside", withoutEnlargement: true }).toFile(outPath);
    return thumbName;
  }
  if (ext === ".svg") {
    const thumbName = `${stem}_thumb.png`;
    const outPath = path.join(THUMB_DIR, thumbName);
    await sharp(savedPath).resize(200, 200, { fit: "inside", withoutEnlargement: true }).png().toFile(outPath);
    return thumbName;
  }
  return null;
}

app.use(express.json());

app.post("/upload", (req, res) => {
  const upload = createUploader(req).single("file");
  upload(req, res, async (err) => {
    if (err) {
      if (err instanceof multer.MulterError && err.code === "LIMIT_FILE_SIZE") {
        return res.status(413).json({ error: "File too large" });
      }
      return res.status(400).json({ error: err.message || String(err) });
    }
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded (use field name: file)" });
    }
    const rel = path.posix.join("uploads", req.file.filename);
    const abs = req.file.path;
    const ext = path.extname(req.file.filename).toLowerCase();
    let thumbnail = null;
    if (IMAGE_EXTS.has(ext)) {
      try {
        thumbnail = await generateImageThumbnail(abs, req.file.filename);
      } catch (e) {
        return res.status(500).json({ error: "Thumbnail failed", detail: e.message });
      }
    }
    return res.json({
      ok: true,
      filename: req.file.filename,
      path: rel,
      url: `/${rel.replace(/\\/g, "/")}`,
      thumbnail: thumbnail ? path.posix.join("uploads/thumbnails", thumbnail) : null,
      enterprise: isEnterpriseUser(req),
    });
  });
});

app.use("/uploads", express.static(UPLOAD_ROOT));

ensureDirs();

if (require.main === module) {
  app.listen(PORT, () => {
    process.stdout.write(`Listening on ${PORT}\n`);
  });
}

module.exports = { app, ensureDirs };
