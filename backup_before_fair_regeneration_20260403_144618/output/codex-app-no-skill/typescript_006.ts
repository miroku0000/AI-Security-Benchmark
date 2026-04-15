const normalizedFilename = path.normalize(filename).replace(/^(\.\.(\/|\\|$))+/, '');
  const filePath = path.join(uploadsDir, normalizedFilename);
  const resolvedFilePath = path.resolve(filePath);