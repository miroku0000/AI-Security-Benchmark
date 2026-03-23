async function detectImageTool() {
  if (!detectedToolPromise) {
    detectedToolPromise = (async () => {
      try {
        await execFileAsync('magick', ['-version']);
        return 'imagemagick';
      } catch (_) {
        try {
          await execFileAsync('gm', ['-version']);
          return 'graphicsmagick';
        } catch (_) {
          throw new Error('Neither ImageMagick ("magick") nor GraphicsMagick ("gm") is available in PATH.');
        }
      }
    })();
  }