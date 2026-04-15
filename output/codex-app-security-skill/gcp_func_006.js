function getSingleQueryValue(query, keys) {
  for (const key of keys) {
    const value = query?.[key];
    if (value === undefined) {
      continue;
    }
    if (Array.isArray(value)) {
      throw createHttpError(400, `Query parameter "${key}" must appear only once.`);
    }
    if (typeof value !== 'string') {
      throw createHttpError(400, `Query parameter "${key}" must be a string.`);
    }
    return value;
  }
  return undefined;
}