const PORT = Number(process.env.PORT || 3000);
const API_KEY = process.env.ADMIN_API_KEY || '';
const ALLOWED_INDICES = new Set(
  (process.env.ALLOWED_INDICES || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
);