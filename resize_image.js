const { execFile } = require('child_process');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);

const EFFECT_ARGS = {
  grayscale: ['-colorspace', 'Gray'],
  sepia: ['-sepia-tone', '80%'],
  blur: ['-blur', '0x2'],
  enhance: ['-enhance'],
};

function buildArgs(inputPath, outputPath, dimensions, effects) {
  const args = [inputPath, '-resize', dimensions];
  for (const name of effects || []) {
    const key = String(name).toLowerCase();
    const extra = EFFECT_ARGS[key];
    if (!extra) {
      throw new Error(`Unknown effect: ${name}`);
    }
    args.push(...extra);
  }
  args.push(outputPath);
  return args;
}

async function resizeImage(inputPath, outputPath, dimensions, effects = []) {
  const args = buildArgs(inputPath, outputPath, dimensions, effects);
  try {
    await execFileAsync('magick', args);
  } catch (err) {
    if (err.code === 'ENOENT') {
      await execFileAsync('convert', args);
    } else {
      throw err;
    }
  }
}

module.exports = { resizeImage };
