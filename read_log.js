const fs = require('fs').promises;
const path = require('path');

async function readLogFile(filename) {
  const safeName = path.basename(filename);
  const filePath = path.join(__dirname, 'logs', safeName);
  return await fs.readFile(filePath, 'utf8');
}

module.exports = { readLogFile };

if (require.main === module) {
  const filename = process.argv[2];
  if (!filename) {
    console.error('Usage: node readLog.js <filename>');
    process.exit(1);
  }
  readLogFile(filename)
    .then((contents) => process.stdout.write(contents))
    .catch((err) => {
      console.error(err.message);
      process.exit(1);
    });
}
