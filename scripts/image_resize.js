const { spawn } = require("child_process");

const EFFECT_ARGS = {
  grayscale: ["-colorspace", "Gray"],
  sepia: ["-sepia-tone", "80%"],
  blur: ["-blur", "0x2"],
  enhance: ["-enhance"],
};

function buildEffectArgs(effects = []) {
  const args = [];

  for (const effect of effects) {
    if (!EFFECT_ARGS[effect]) {
      throw new Error(
        `Unsupported effect: ${effect}. Supported effects: ${Object.keys(EFFECT_ARGS).join(", ")}`
      );
    }
    args.push(...EFFECT_ARGS[effect]);
  }

  return args;
}

function runCommand(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stderr = "";

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => {
      reject(err);
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(
        new Error(`${command} failed with exit code ${code}${stderr ? `: ${stderr.trim()}` : ""}`)
      );
    });
  });
}

async function resizeImage(inputFile, outputFile, dimensions, effects = []) {
  if (!inputFile || !outputFile || !dimensions) {
    throw new Error("resizeImage requires inputFile, outputFile, and dimensions (e.g. 200x200).");
  }

  const effectArgs = buildEffectArgs(effects);
  const imageMagickArgs = [inputFile, "-resize", dimensions, ...effectArgs, outputFile];

  try {
    // Prefer ImageMagick first for broader feature support.
    await runCommand("magick", imageMagickArgs);
  } catch (imError) {
    // Fallback for systems where GraphicsMagick is installed as `gm`.
    const gmArgs = ["convert", ...imageMagickArgs];
    try {
      await runCommand("gm", gmArgs);
    } catch (gmError) {
      throw new Error(
        `Image conversion failed. Tried ImageMagick (magick) and GraphicsMagick (gm).\n` +
          `magick error: ${imError.message}\n` +
          `gm error: ${gmError.message}`
      );
    }
  }
}

module.exports = { resizeImage };

// Example usage:
// resizeImage("user_photo.jpg", "thumb.jpg", "200x200", ["grayscale", "enhance"])
//   .then(() => console.log("Image processed"))
//   .catch((err) => console.error(err.message));
