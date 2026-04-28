const execFileAsync = promisify(execFile);

async function detectImageTool() {
  const candidates = [
    { command: 'magick', prefixArgs: ['convert'], versionArgs: ['-version'] },
    { command: 'gm', prefixArgs: ['convert'], versionArgs: ['version'] },
    { command: 'convert', prefixArgs: [], versionArgs: ['-version'] },
  ];

  for (const tool of candidates) {
    try {
      await execFileAsync(tool.command, tool.versionArgs);
      return tool;
    } catch (_) {
      // Try next candidate
    }
  }

  throw new Error(
    'ImageMagick or GraphicsMagick is not installed or not available in PATH.'
  );
}

function buildEffectArgs(effects = []) {
  const args = [];

  for (const effect of effects) {
    switch (String(effect).toLowerCase()) {
      case 'grayscale':
        args.push('-colorspace', 'Gray');
        break;
      case 'sepia':
        args.push('-sepia-tone', '80%');
        break;
      case 'blur':
        args.push('-blur', '0x2');
        break;
      case 'enhance':
        args.push('-enhance');
        break;
      default:
        throw new Error(`Unsupported effect: ${effect}`);
    }
  }

  return args;
}

async function resizeImage(inputFile, outputFile, dimensions, effects = []) {
  if (!inputFile || !outputFile || !dimensions) {
    throw new Error('inputFile, outputFile, and dimensions are required.');
  }

  const tool = await detectImageTool();
  const args = [
    ...tool.prefixArgs,
    inputFile,
    '-resize',
    dimensions,
    ...buildEffectArgs(effects),
    outputFile,
  ];

  await execFileAsync(tool.command, args);
  return outputFile;
}

module.exports = { resizeImage };

if (require.main === module) {
  resizeImage('user_photo.jpg', 'thumb.jpg', '200x200', ['grayscale', 'enhance'])
    .then((output) => {
      console.log(`Image written to ${output}`);
    })
    .catch((error) => {
      console.error(error.message);
      process.exit(1);
    });
}