function requireInteger(value, fieldName, options = {}) {
  if (!Number.isInteger(value)) {
    throw new ValidationError(`${fieldName} must be an integer`);
  }
  if (options.min !== undefined && value < options.min) {
    throw new ValidationError(`${fieldName} must be >= ${options.min}`);
  }
  if (options.max !== undefined && value > options.max) {
    throw new ValidationError(`${fieldName} must be <= ${options.max}`);
  }
  return value;
}