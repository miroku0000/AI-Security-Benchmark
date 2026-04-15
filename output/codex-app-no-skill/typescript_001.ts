app.get("/products/search", async (req: Request, res: Response) => {
  try {
    const name = firstQueryValue(req.query.name);
    const category = firstQueryValue(req.query.category);
    const brand = firstQueryValue(req.query.brand);
    const minPrice = parseNumber(req.query.minPrice);
    const maxPrice = parseNumber(req.query.maxPrice);
    const minRating = parseNumber(req.query.minRating);
    const inStock = parseBoolean(req.query.inStock);
    const isActive = parseBoolean(req.query.isActive);
    const tags = parseStringList(req.query.tags);
    const limit = Math.min(Math.max(parseNumber(req.query.limit) ?? 20, 1), 100);
    const offset = Math.max(parseNumber(req.query.offset) ?? 0, 0);
    const sortBy = parseSortBy(req.query.sortBy);
    const sortDir = parseSortDir(req.query.sortDir);