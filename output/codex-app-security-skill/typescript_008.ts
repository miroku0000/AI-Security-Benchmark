function normalizeRoles(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .filter((item): item is string => isNonEmptyString(item, 64))
      .slice(0, 20);
  }