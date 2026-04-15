const email = normalizeEmail(input.email);
  const displayName = normalizeDisplayName(input.displayName);
  const status = normalizeFilterValue("status", input.status);
  const role = normalizeFilterValue("role", input.role);
  const country = normalizeFilterValue("country", input.country);
  const tier = normalizeFilterValue("tier", input.tier);