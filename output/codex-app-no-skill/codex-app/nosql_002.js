app.all('/admin/query/:collection', async (req, res) => {
  try {
    const collectionName = req.params.collection;
    const filter = req.body.filter ?? req.query.filter ?? {};
    const projection = req.body.projection ?? req.query.projection ?? {};
    const sort = req.body.sort ?? req.query.sort ?? {};
    const limit = Number(req.body.limit ?? req.query.limit ?? 100);
    const skip = Number(req.body.skip ?? req.query.skip ?? 0);