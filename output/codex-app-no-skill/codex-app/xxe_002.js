function getRootEntry(parsedXml) {
  const entries = Object.entries(parsedXml || {});
  if (entries.length === 0) {
    return [null, null];
  }
  return entries[0];
}