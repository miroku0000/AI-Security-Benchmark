const results = [];
  for (const item of value) {
    if (typeof item !== 'string') {
      throw new Error(`${field} entries must be strings`);
    }
    const normalized = item.trim();
    if (!normalized) {
      throw new Error(`${field} entries must not be empty`);
    }
    if (!validator(normalized)) {
      throw new Error(`${field} contains an invalid value`);
    }
    results.push(normalized);
  }