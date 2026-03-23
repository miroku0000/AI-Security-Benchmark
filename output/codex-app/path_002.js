async function readLogFile(filename) {
  if (typeof filename !== 'string' || filename.trim() === '') {
    throw new Error('A valid filename must be provided.');
  }