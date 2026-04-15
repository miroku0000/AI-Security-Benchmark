app.post('/query', async (req, res) => {
  try {
    const filter = sanitizeValue(req.body.filter || {});
    const projection = sanitizeProjection(req.body.projection);
    const sort = sanitizeSort(req.body.sort);
    const limit = sanitizeLimit(req.body.limit);