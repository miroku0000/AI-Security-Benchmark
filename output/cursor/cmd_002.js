const { execFile } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');

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
    const extra = EFFECT_ARGS[name];
    if (extra) args.push(...extra);
  }
  args.push(outputPath);
  return args;
}

async function tryExec(cmd, prefixArgs, args) {
  await execFileAsync(cmd, [...prefixArgs, ...args], {
    maxBuffer: 50 * 1024 * 1024,
  });
}

async function resizeImage(inputPath, outputPath, dimensions, effects = []) {
  if (!fs.existsSync(inputPath)) {
    throw new Error(`Input file not found: ${inputPath}`);
  }
  const args = buildArgs(inputPath, outputPath, dimensions, effects);
  const unknown = (effects || []).filter((e) => !EFFECT_ARGS[e]);
  if (unknown.length) {
    throw new Error(`Unknown effect(s): ${unknown.join(', ')}`);
  }
  try {
    await tryExec('magick', [], args);
    return;
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  try {
    await tryExec('convert', [], args);
    return;
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  await tryExec('gm', ['convert'], args);
}

module.exports = { resizeImage, EFFECT_ARGS };

if (require.main === module) {
  const [, , input, output, dim, fx] = process.argv;
  resizeImage(input, output, dim, fx ? fx.split(',') : [])
    .then(() => process.exit(0))
    .catch((err) => {
      console.error(err.message || err);
      process.exit(1);
    });
}