const storage = multer.diskStorage({
  destination(req, file, cb) {
    cb(null, UPLOAD_DIR);
  },
  filename(req, file, cb) {
    const ext = path.extname(file.originalname).toLowerCase();
    const baseName = sanitizeFilenamePart(path.basename(file.originalname, ext));
    cb(null, `${baseName}-${Date.now()}${ext}`);
  }
});