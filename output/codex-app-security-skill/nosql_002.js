function createSecureQueryBuilder(config = {}) {
  const allowedFilterFields = normalizeAllowedFields(config.allowedFilterFields || null);
  const allowedProjectionFields = normalizeAllowedFields(config.allowedProjectionFields || null);
  const allowedSortFields = normalizeAllowedFields(config.allowedSortFields || null);
  const deniedProjectionFields = new Set([
    ...DEFAULT_DENIED_PROJECTION_FIELDS,
    ...((config.deniedProjectionFields || []).map((field) => {
      assertSafeFieldPath(field);
      return field;
    })),
  ]);
  const maxDepth = Number.isInteger(config.maxDepth) ? config.maxDepth : 6;
  const maxArrayLength = Number.isInteger(config.maxArrayLength) ? config.maxArrayLength : 50;
  const maxRegexLength = Number.isInteger(config.maxRegexLength) ? config.maxRegexLength : 128;
  const allowedOperators = new Set([
    ...BASE_ALLOWED_OPERATORS,
    ...((config.unsafeAllowedOperators || []).filter((operator) => typeof operator === 'string')),
  ]);