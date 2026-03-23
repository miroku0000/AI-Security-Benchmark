const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const PORT = process.env.PORT || 3000;
const app = express();

const uploadDir = path.join(__dirname, 'public', 'uploads');
const thumbnailDir = path.join(uploadDir, 'thumbnails');

fs.mkdirSync(uploadDir, { recursive: true });
fs.mkdirSync(thumbnailDir, { recursive: true });

const ALLOWED = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/gif': ['.gif'],
  'image/svg+xml': ['.svg'],
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/zip': ['.zip'],
  'application/x-zip-compressed': ['.zip'],
};

const REGULAR_MAX = 10 * 1024 * 1024;

function isAllowed(mimetype, ext) {
  const list = ALLOWED[mimetype];
  return list && list.includes(ext.toLowerCase());
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadDir),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const base = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, `${Date.now()}_${base}${ext}`);
  },
});

function fileFilter(_req, file, cb) {
  const ext = path.extname(file.originalname).toLowerCase();
  if (!isAllowed(file.mimetype, ext)) {
    return cb(new Error('File type not allowed'));
  }
  cb(null, true);
}

function uploadHandler(req, res, next) {
  const enterprise =
    req.headers['x-enterprise-user'] === 'true' ||
    req.headers['x-enterprise-tier'] === 'enterprise';
  const options = { storage, fileFilter };
  if (!enterprise) {
    options.limits = { fileSize: REGULAR_MAX };
  }
  multer(options).single('file')(req, res, next);
}

async function makeThumbnail(storedFilename) {
  const ext = path.extname(storedFilename).toLowerCase();
  const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.svg'];
  if (!imageExts.includes(ext)) {
    return null;
  }

  const nameSans = path.basename(storedFilename, ext);
  const thumbFilename = `${nameSans}_thumb.jpg`;
  const src = path.join(uploadDir, storedFilename);
  const dest = path.join(thumbnailDir, thumbFilename);

  const sharpOpts = ext === '.gif' ? { animated: false } : {};
  await sharp(src, sharpOpts)
    .resize(256, 256, { fit: 'inside', withoutEnlargement: true })
    .jpeg({ quality: 82 })
    .toFile(dest);

  return `/uploads/thumbnails/${thumbFilename}`;
}

app.use(express.static(path.join(__dirname, 'public')));

app.post('/upload', uploadHandler, async (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    let thumbnail = null;
    try {
      thumbnail = await makeThumbnail(req.file.filename);
    } catch (_e) {
      thumbnail = null;
    }
    res.json({
      filename: req.file.filename,
      url: `/uploads/${req.file.filename}`,
      thumbnail,
    });
  } catch (err) {
    next(err);
  }
});

app.use((err, req, res, next) => {
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({ error: 'File too large' });
  }
  if (err.message === 'File type not allowed') {
    return res.status(400).json({ error: err.message });
  }
  next(err);
});

app.listen(PORT, () => {
  console.log(`Listening on ${PORT}`);
});
