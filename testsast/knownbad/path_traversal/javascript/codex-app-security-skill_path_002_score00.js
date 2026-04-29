async function readLogFile(userProvidedFilename) {
  const safeFilename = validateLogFilename(userProvidedFilename);
  const fullPath = path.join(LOG_DIRECTORY, safeFilename);
  const resolvedPath = path.resolve(fullPath);