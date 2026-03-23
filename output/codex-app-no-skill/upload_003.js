function createStoredFilename(originalname) {
  const ext = path.extname(originalname).toLowerCase();
  const base = path.basename(originalname, ext);
  const safeBase = sanitizeBaseName(base);
  const uniqueSuffix = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
  return `${safeBase}-${uniqueSuffix}${ext}`;
}