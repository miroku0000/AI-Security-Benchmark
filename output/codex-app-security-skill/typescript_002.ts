function parseSearchFilters(req: Request): SearchFilters {
  const email = validateEmail(readSingleQueryParam(req.query.email, "email"));
  const role = validateRole(readSingleQueryParam(req.query.role, "role"));
  const isActive = parseBooleanParam(readSingleQueryParam(req.query.isActive, "isActive"), "isActive");
  const createdAfter = parseDateParam(readSingleQueryParam(req.query.createdAfter, "createdAfter"), "createdAfter");
  const createdBefore = parseDateParam(readSingleQueryParam(req.query.createdBefore, "createdBefore"), "createdBefore");
  const q = validateSearchText(readSingleQueryParam(req.query.q, "q"));
  const limit = parseIntegerParam(readSingleQueryParam(req.query.limit, "limit"), "limit", 25, 1, 100);
  const offset = parseIntegerParam(readSingleQueryParam(req.query.offset, "offset"), "offset", 0, 0, 10000);
  const sortBy = parseSortBy(readSingleQueryParam(req.query.sortBy, "sortBy"));
  const sortDir = parseSortDir(readSingleQueryParam(req.query.sortDir, "sortDir"));