const result = {};
  for (const [key, value] of Object.entries(projection)) {
    if (typeof key !== 'string' || key.trim() === '' || key.includes('\0') || key.startsWith('$')) {
      throw new Error(`Invalid projection field: ${key}`);
    }