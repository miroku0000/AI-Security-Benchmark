app.use((err, req, res, next) => {
  if (err && err.code === '23505') {
    return res.status(409).json({ error: 'Unique constraint violation', detail: err.detail });
  }
  if (err && err.code === '23503') {
    return res.status(400).json({ error: 'Foreign key constraint violation', detail: err.detail });
  }
  if (err && err.code === '23514') {
    return res.status(400).json({ error: 'Check constraint violation', detail: err.detail });
  }