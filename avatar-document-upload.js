const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const sharp = require("sharp");

const app = express();
app.use(express.static(path.join(__dirname, "public")));
const UPLOAD_ROOT = path.join(__dirname, "public", "uploads");
const THUMB_DIR = path.join(UPLOAD_ROOT, "thumbnails");
const NON_ENTERPRISE_MAX_BYTES = 25 * 1024 * 1024;

const IMAGE_EXT = new Set([".jpg", ".jpeg", ".png", ".gif", ".svg"]);
const ALLOWED_EXT = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".svg",
  ".pdf",
  ".doc",
  ".docx",
  ".zip",
]);

function ensureDirs() {
  fs.mkdirSync(UPLOAD_ROOT, { recursive: true });
  fs.mkdirSync(THUMB_DIR, { recursive: true });
}

function isEnterprise(req) {
  const h = String(req.get("x-enterprise-user") || "").toLowerCase();
  return h === "true" || h === "1" || h === "yes";
}

function allowedFile(filename) {
  const ext = path.extname(filename).toLowerCase();
  return ALLOWED_EXT.has(ext);
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    ensureDirs();
    cb(null, UPLOAD_ROOT);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const base = path.basename(file.originalname, ext).replace(/[^\w.-]+/g, "_");
    const unique = `${Date.now()}_${base}${ext}`;
    cb(null, unique);
  },
});

function dynamicUploadSingle(req, res, next) {
  const limits = isEnterprise(req) ? {} : { fileSize: NON_ENTERPRISE_MAX_BYTES };
  const m = multer({
    storage,
    limits,
    fileFilter: (req, file, cb) => {
      if (!allowedFile(file.originalname)) {
        return cb(new multer.MulterError("LIMIT_UNEXPECTED_FILE", file.fieldname));
      }
      cb(null, true);
    },
  });
  m.single("file")(req, res, next);
}

async function createThumbnail(imagePath, originalFilename) {
  const ext = path.extname(originalFilename).toLowerCase();
  const base = path.basename(originalFilename, ext);
  const thumbName = `${base}_thumb${ext === ".svg" ? ".png" : ext === ".gif" ? ".png" : ext}`;
  const thumbPath = path.join(THUMB_DIR, thumbName);

  if (ext === ".svg") {
    await sharp(imagePath, { density: 150 })
      .resize(256, 256, { fit: "inside", withoutEnlargement: true })
      .png()
      .toFile(thumbPath);
  } else if (ext === ".gif") {
    await sharp(imagePath, { pages: 1 })
      .rotate()
      .resize(256, 256, { fit: "inside", withoutEnlargement: true })
      .png()
      .toFile(thumbPath);
  } else {
    await sharp(imagePath)
      .rotate()
      .resize(256, 256, { fit: "inside", withoutEnlargement: true })
      .toFile(thumbPath);
  }
  return path.relative(path.join(__dirname, "public"), thumbPath).replace(/\\/g, "/");
}

app.post("/upload", dynamicUploadSingle, async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }
    const savedName = req.file.filename;
    const ext = path.extname(savedName).toLowerCase();
    const publicPath = `/uploads/${savedName}`;
    let thumbnailUrl = null;

    if (IMAGE_EXT.has(ext)) {
      try {
        const thumbRel = await createThumbnail(req.file.path, savedName);
        thumbnailUrl = `/${thumbRel}`;
      } catch (e) {
        return res.status(500).json({
          error: "Thumbnail generation failed",
          file: publicPath,
          detail: String(e && e.message ? e.message : e),
        });
      }
    }

    return res.json({
      ok: true,
      file: publicPath,
      thumbnail: thumbnailUrl,
      enterprise: isEnterprise(req),
    });
  } catch (err) {
    if (req.file && req.file.path) {
      try {
        fs.unlinkSync(req.file.path);
      } catch (_) {}
    }
    return res.status(500).json({ error: String(err && err.message ? err.message : err) });
  }
});

app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === "LIMIT_FILE_SIZE") {
      return res.status(413).json({ error: "File too large (enterprise users have no limit)" });
    }
    return res.status(400).json({ error: err.message, code: err.code });
  }
  next(err);
});

const PORT = process.env.PORT || 3000;
ensureDirs();
app.listen(PORT, () => {});
