const fs = require('fs/promises');
const path = require('path');

/**
 * @param {string} filename - Name or path of the log file (relative to cwd or absolute).
 * @returns {Promise<string>}
 */
async function readLogFile(filename) {
  if (!filename || typeof filename !== 'string') {
    throw new TypeError('filename must be a non-empty string');
  }
  const resolved = path.resolve(filename);
  return fs.readFile(resolved, { encoding: 'utf8' });
}

module.exports = { readLogFile };