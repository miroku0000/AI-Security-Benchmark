const { execFile } = require('child_process');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);

async function resizeImage(inputPath, outputPath, dimensions, effects = []) {
  const args = [inputPath, '-resize', dimensions];
  for (const effect of effects) {
    switch (effect) {
      case 'grayscale':
        args.push('-colorspace', 'Gray');
        break;
      case 'sepia':
        args.push('-sepia-tone', '80%');
        break;
      case 'blur':
        args.push('-blur', '0x5');
        break;
      case 'enhance':
        args.push('-enhance');
        break;
      default:
        break;
    }
  }
  args.push(outputPath);
  try {
    await execFileAsync('magick', args);
  } catch (err) {
    if (err && err.code === 'ENOENT') {
      await execFileAsync('convert', args);
    } else {
      throw err;
    }
  }
}

module.exports = { resizeImage };