function extractSchemaReferences(parsedXml) {
  const rootName = Object.keys(parsedXml)[0];
  const root = parsedXml[rootName] || {};
  const attrs = root.$ || {};
  const refs = [];