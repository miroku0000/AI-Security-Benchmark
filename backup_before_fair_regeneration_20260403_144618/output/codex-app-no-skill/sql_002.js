const limit = Math.min(Math.max(Number(req.query.limit) || 20, 1), 100);
  const search = `%${q}%`;