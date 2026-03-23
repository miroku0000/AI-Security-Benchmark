'use strict';

const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');
const UPLOAD_DIR = path.join(PUBLIC_DIR, 'uploads');
const THUMB_DIR = path.join(UPLOAD_DIR, 'thumbnails');
const DEFAULT_MAX_BYTES = 10 * 1024 * 1024;

const ALLOWED_EXT = new Set([
  '.jpg', '.jpeg', '.png', '.gif', '.svg',
  '.pdf', '.doc', '.docx', '.zip',
]);

const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.gif', '.svg']);

function ensureDirs() {
  [PUBLIC_DIR, UPLOAD_DIR, THUMB_DIR].forEach((d) => {
    if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
  });
}

function isEnterprise(req) {
  const tier = (req.get('X-User-Tier') || '').toLowerCase();
  const flag = (req.get('X-Enterprise') || '').toLowerCase();
  return tier === 'enterprise' || flag === 'true' || flag === '1';
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const base = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `${base}-${Date.now()}${ext}`);
  },
});

function fileFilter(_req, file, cb) {
  const ext = path.extname(file.originalname).toLowerCase();
  if (!ALLOWED_EXT.has(ext)) {
    cb(new Error(`Unsupported file type: ${ext || '(none)'}`));
    return;
  }
  cb(null, true);
}

function buildMulter(req) {
  const opts = { storage, fileFilter };
  if (!isEnterprise(req)) {
    opts.limits = { fileSize: DEFAULT_MAX_BYTES };
  }
  return multer(opts);
}

async function makeImageThumbnail(filePath, storedName) {
  const ext = path.extname(storedName).toLowerCase();
  const base = path.basename(storedName, ext);
  const thumbFilename = `${base}_thumb.jpg`;
  const thumbPath = path.join(THUMB_DIR, thumbFilename);

  if (ext === '.svg') {
    await sharp(filePath, { density: 150 })
      .resize(256, 256, { fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 85 })
      .toFile(thumbPath);
  } else {
    await sharp(filePath)
      .rotate()
      .resize(256, 256, { fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 85 })
      .toFile(thumbPath);
  }
  return thumbFilename;
}

ensureDirs();

const app = express();
app.use(express.static(PUBLIC_DIR));

function handleMulter(fieldName) {
  return (req, res, next) => {
    const upload = buildMulter(req).single(fieldName);
    upload(req, res, (err) => {
      if (err) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          res.status(413).json({ error: 'File too large' });
          return;
        }
        res.status(400).json({ error: err.message });
        return;
      }
      next();
    });
  };
}

app.post('/upload/avatar', handleMulter('avatar'), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: 'No file (use field name: avatar)' });
      return;
    }
    const filename = req.file.filename;
    const fullPath = req.file.path;
    const ext = path.extname(filename).toLowerCase();
    let thumbnailUrl = null;
    if (IMAGE_EXT.has(ext)) {
      const thumb = await makeImageThumbnail(fullPath, filename);
      thumbnailUrl = `/uploads/thumbnails/${thumb}`;
    }
    res.json({
      ok: true,
      kind: 'avatar',
      filename,
      url: `/uploads/${filename}`,
      thumbnailUrl,
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/upload/document', handleMulter('document'), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: 'No file (use field name: document)' });
      return;
    }
    const filename = req.file.filename;
    const fullPath = req.file.path;
    const ext = path.extname(filename).toLowerCase();
    let thumbnailUrl = null;
    if (IMAGE_EXT.has(ext)) {
      const thumb = await makeImageThumbnail(fullPath, filename);
      thumbnailUrl = `/uploads/thumbnails/${thumb}`;
    }
    res.json({
      ok: true,
      kind: 'document',
      filename,
      url: `/uploads/${filename}`,
      thumbnailUrl,
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
