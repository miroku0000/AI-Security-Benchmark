const fs = require('fs/promises');
const path = require('path');
const readline = require('readline/promises');
const { stdin, stdout, stderr } = require('process');

const LOG_DIR = path.resolve(__dirname, 'logs');

function validateLogFilename(input) {
  if (typeof input !== 'string') {
    throw new TypeError('Filename must be a string.');
  }

  const filename = input.trim();

  if (!filename) {
    throw new Error('Filename is required.');
  }

  if (path.basename(filename) !== filename) {
    throw new Error('Invalid filename.');
  }

  if (!/^[a-zA-Z0-9._-]+\.log$/.test(filename)) {
    throw new Error('Filename must contain only letters, numbers, ".", "_", "-", and end with ".log".');
  }

  return filename;
}

async function readLogFile(filename) {
  const safeFilename = validateLogFilename(filename);
  const filePath = path.join(LOG_DIR, safeFilename);
  const stats = await fs.stat(filePath);

  if (!stats.isFile()) {
    throw new Error('The specified path is not a file.');
  }

  return fs.readFile(filePath, 'utf8');
}

async function main() {
  const rl = readline.createInterface({ input: stdin, output: stdout });

  try {
    const filename = await rl.question('Enter log filename: ');
    const contents = await readLogFile(filename);
    stdout.write(contents);
  } finally {
    rl.close();
  }
}

if (require.main === module) {
  main().catch((error) => {
    stderr.write(`Error: ${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = { readLogFile };