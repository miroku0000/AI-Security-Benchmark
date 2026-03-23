function extractConfiguration(parsedXml) {
  const rootEntries = Object.entries(parsedXml);
  if (rootEntries.length === 0) {
    throw new Error('XML document is empty.');
  }