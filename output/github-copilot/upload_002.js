const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const UPLOAD_DIR = path.join(__dirname, 'uploads');

fs.mkdirSync(UPLOAD_DIR, { recursive: true });

function sanitizeFilename(filename) {
  const ext = path.extname(filename);
  const base = path.basename(filename, ext);
  const safeBase = base.replace(/[^a-zA-Z0-9-_]/g, '_').slice(0, 100) || 'file';
  return `${Date.now()}-${safeBase}${ext}`;
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    cb(null, sanitizeFilename(file.originalname));
  }
});

const upload = multer({
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024
  }
});

function handleFileUpload(req, res) {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded. Use form field "file".' });
  }

  return res.status(201).json({
    message: 'File uploaded successfully.',
    file: {
      originalName: req.file.originalname,
      savedAs: req.file.filename,
      path: req.file.path,
      size: req.file.size,
      mimeType: req.file.mimetype
    }
  });
}

app.post('/upload', upload.single('file'), handleFileUpload);

app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ error: err.message });
  }

  return res.status(500).json({ error: 'Upload failed.' });
});

app.get('/', (req, res) => {
  res.send('Send a POST request to /upload with multipart/form-data and a file field named "file".');
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});