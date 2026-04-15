function buildFilename(originalname) {
  const ext = path.extname(originalname).toLowerCase();
  const base = sanitizeBaseName(originalname);
  return `${base}-${Date.now()}-${Math.round(Math.random() * 1e9)}${ext}`;
}