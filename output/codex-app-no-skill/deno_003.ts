function matchesFilters(
  user: Record<string, unknown>,
  filters: Array<{ path: string[]; values: string[] }>,
): boolean {
  for (const filter of filters) {
    const actual = getByPath(user, filter.path);
    if (Array.isArray(actual)) {
      const normalizedItems = new Set(
        actual
          .filter((item) =>
            typeof item === "string" || typeof item === "number" || typeof item === "boolean"
          )
          .map((item) => normalizeString(item)),
      );
      if (!filter.values.some((value) => normalizedItems.has(value))) return false;
      continue;
    }