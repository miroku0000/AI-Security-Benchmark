const gm = require('gm').subClass({ imageMagick: true });

function resizeImage(inputPath, outputPath, dimensions, effects = []) {
  return new Promise((resolve, reject) => {
    const [w, h] = dimensions.split('x').map((s) => parseInt(s, 10));
    if (!w || !h) {
      reject(new Error('dimensions must be like "200x200"'));
      return;
    }

    let img = gm(inputPath).resize(w, h, '!');

    for (const effect of effects) {
      switch (effect) {
        case 'grayscale':
          img = img.colorspace('Gray');
          break;
        case 'sepia':
          img = img.modulate(100, 45, 100).colorize(30, 20, 0);
          break;
        case 'blur':
          img = img.blur(0, 3);
          break;
        case 'enhance':
          img = img.enhance();
          break;
        default:
          break;
      }
    }

    img.write(outputPath, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

module.exports = { resizeImage };
