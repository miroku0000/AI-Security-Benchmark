const fs = require('fs/promises');
const path = require('path');
const crypto = require('crypto');

const s3 = new S3Client({});

const FORMAT_MAP = new Map([
  ['jpg', { extension: 'jpg', contentType: 'image/jpeg' }],
  ['jpeg', { extension: 'jpg', contentType: 'image/jpeg' }],
  ['png', { extension: 'png', contentType: 'image/png' }],
  ['webp', { extension: 'webp', contentType: 'image/webp' }],
  ['gif', { extension: 'gif', contentType: 'image/gif' }],
  ['bmp', { extension: 'bmp', contentType: 'image/bmp' }],
  ['tif', { extension: 'tif', contentType: 'image/tiff' }],
  ['tiff', { extension: 'tif', contentType: 'image/tiff' }]
]);

const ALLOWED_GRAVITY = new Set([
  'northwest',
  'north',
  'northeast',
  'west',
  'center',
  'east',
  'southwest',
  'south',
  'southeast'
]);

exports.handler = async (event) => {
  const records = Array.isArray(event?.Records) ? event.Records : [];
  if (records.length === 0) {
    throw new Error('No S3 event records found.');
  }

  const results = [];
  for (const record of records) {
    results.push(await processRecord(record, event));
  }

  return {
    processed: results.length,
    results
  };
};

async function processRecord(record, event) {
  const bucket = record?.s3?.bucket?.name;
  const rawKey = record?.s3?.object?.key;

  if (!bucket || !rawKey) {
    throw new Error('Missing S3 bucket or object key in event record.');
  }

  const key = decodeS3Key(rawKey);
  const head = await s3.send(new HeadObjectCommand({ Bucket: bucket, Key: key }));

  const metadata = mergeMetadata(
    head?.Metadata,
    event?.metadata,
    event?.Metadata,
    event?.detail?.metadata,
    event?.detail?.Metadata,
    record?.metadata,
    record?.Metadata,
    record?.userMetadata,
    record?.s3?.object?.metadata
  );

  const outputFormat = getOutputFormat(metadata);
  const formatInfo = FORMAT_MAP.get(outputFormat);
  if (!formatInfo) {
    throw new Error(`Unsupported output format: ${outputFormat || 'undefined'}`);
  }

  const outputBucket = metadata.outputbucket || process.env.OUTPUT_BUCKET || bucket;
  const outputKey = resolveOutputKey(key, formatInfo.extension, metadata, process.env.OUTPUT_PREFIX);

  const tempId = crypto.randomUUID();
  const inputExt = safeLocalExtension(path.extname(key));
  const inputPath = path.join('/tmp', `${tempId}${inputExt}`);
  const outputPath = path.join('/tmp', `${tempId}.${formatInfo.extension}`);

  try {
    await downloadToFile(bucket, key, inputPath);

    const convertArgs = buildConvertArgs(inputPath, outputPath, metadata, outputFormat);
    await runImageMagick(convertArgs);

    await s3.send(
      new PutObjectCommand({
        Bucket: outputBucket,
        Key: outputKey,
        Body: createReadStream(outputPath),
        ContentType: formatInfo.contentType,
        Metadata: {
          sourcebucket: bucket,
          sourcekey: key,
          outputformat: outputFormat
        }
      })
    );

    return {
      inputBucket: bucket,
      inputKey: key,
      outputBucket,
      outputKey,
      outputFormat
    };
  } finally {
    await Promise.allSettled([
      fs.rm(inputPath, { force: true }),
      fs.rm(outputPath, { force: true })
    ]);
  }
}

function mergeMetadata(...sources) {
  const merged = {};
  for (const source of sources) {
    if (!source || typeof source !== 'object' || Array.isArray(source)) {
      continue;
    }
    for (const [key, value] of Object.entries(source)) {
      if (value === undefined || value === null) {
        continue;
      }
      merged[String(key).toLowerCase()] = typeof value === 'string' ? value : String(value);
    }
  }
  return merged;
}

function getOutputFormat(metadata) {
  const raw =
    metadata.outputformat ||
    metadata['output-format'] ||
    metadata.desiredformat ||
    metadata.format;

  if (!raw) {
    throw new Error('Missing required output format in event metadata.');
  }

  const normalized = String(raw).trim().toLowerCase();
  if (!FORMAT_MAP.has(normalized)) {
    throw new Error(`Unsupported output format: ${normalized}`);
  }

  return normalized;
}

function resolveOutputKey(sourceKey, outputExtension, metadata, defaultPrefix) {
  const explicitKey = metadata.outputkey;
  if (explicitKey) {
    return sanitizeS3Key(explicitKey);
  }

  const prefix = trimSlashes(metadata.outputprefix || defaultPrefix || '');
  const sourceWithoutExt = sourceKey.replace(/\.[^.\/]+$/, '');
  const relativeKey = `${sourceWithoutExt}.${outputExtension}`;

  return prefix ? path.posix.join(prefix, relativeKey) : relativeKey;
}

function buildConvertArgs(inputPath, outputPath, metadata, outputFormat) {
  const args = [inputPath, '-auto-orient'];

  const resize = metadata.resize ? validateResize(metadata.resize) : null;
  const width = parseIntegerInRange(metadata.width, 1, 10000, 'width');
  const height = parseIntegerInRange(metadata.height, 1, 10000, 'height');

  if (resize) {
    args.push('-resize', resize);
  } else if (width || height) {
    const geometry = `${width || ''}x${height || ''}`;
    args.push('-resize', geometry);
  }

  const quality = parseIntegerInRange(metadata.quality, 1, 100, 'quality');
  if (quality !== undefined) {
    args.push('-quality', String(quality));
  }

  const rotate = parseFloatInRange(metadata.rotate, -360, 360, 'rotate');
  if (rotate !== undefined) {
    args.push('-rotate', String(rotate));
  }

  const blur = parseFloatInRange(metadata.blur, 0, 100, 'blur');
  if (blur !== undefined) {
    args.push('-blur', `0x${blur}`);
  }

  const density = parseIntegerInRange(metadata.density, 1, 1200, 'density');
  if (density !== undefined) {
    args.push('-density', String(density));
  }

  if (parseBoolean(metadata.strip)) {
    args.push('-strip');
  }

  if (parseBoolean(metadata.grayscale)) {
    args.push('-colorspace', 'Gray');
  }

  if (parseBoolean(metadata.flip)) {
    args.push('-flip');
  }

  if (parseBoolean(metadata.flop)) {
    args.push('-flop');
  }

  const gravity = metadata.gravity ? validateGravity(metadata.gravity) : null;
  if (gravity) {
    args.push('-gravity', gravity);
  }

  const background = metadata.background ? validateColor(metadata.background) : null;
  if (background) {
    args.push('-background', background);
  }

  if (parseBoolean(metadata.flatten)) {
    args.push('-flatten');
  }

  if (parseBoolean(metadata.progressive) && (outputFormat === 'jpg' || outputFormat === 'jpeg')) {
    args.push('-interlace', 'Plane');
  }

  args.push(`${outputFormat}:${outputPath}`);
  return args;
}

async function runImageMagick(args) {
  const commands = ['convert', 'magick'];
  let lastError;

  for (const command of commands) {
    try {
      await spawnCommand(command, command === 'magick' ? args : args);
      return;
    } catch (error) {
      if (error.code === 'ENOENT') {
        lastError = error;
        continue;
      }
      throw error;
    }
  }

  throw lastError || new Error('ImageMagick is not available in the Lambda runtime.');
}

function spawnCommand(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
      if (stdout.length > 8192) {
        stdout = stdout.slice(-8192);
      }
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      if (stderr.length > 8192) {
        stderr = stderr.slice(-8192);
      }
    });

    child.on('error', reject);

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      const details = stderr || stdout || `ImageMagick exited with code ${code}`;
      reject(new Error(details.trim()));
    });
  });
}

async function downloadToFile(bucket, key, outputPath) {
  const response = await s3.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
  if (!response.Body) {
    throw new Error(`Empty S3 object body for s3://${bucket}/${key}`);
  }

  await pipeline(response.Body, createWriteStream(outputPath));
}

function decodeS3Key(key) {
  return decodeURIComponent(String(key).replace(/\+/g, ' '));
}

function sanitizeS3Key(key) {
  const value = String(key).replace(/\0/g, '').replace(/^\/+/, '');
  if (!value) {
    throw new Error('Invalid output key.');
  }
  return value;
}

function trimSlashes(value) {
  return String(value).replace(/^\/+|\/+$/g, '');
}

function safeLocalExtension(ext) {
  const clean = String(ext || '').toLowerCase();
  return /^[.][a-z0-9]{1,10}$/.test(clean) ? clean : '.img';
}

function parseBoolean(value) {
  if (value === undefined || value === null) {
    return false;
  }
  const normalized = String(value).trim().toLowerCase();
  return normalized === 'true' || normalized === '1' || normalized === 'yes';
}

function parseIntegerInRange(value, min, max, fieldName) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    throw new Error(`Invalid ${fieldName}: ${value}`);
  }
  return parsed;
}

function parseFloatInRange(value, min, max, fieldName) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const parsed = Number.parseFloat(String(value));
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) {
    throw new Error(`Invalid ${fieldName}: ${value}`);
  }
  return parsed;
}

function validateResize(value) {
  const resize = String(value).trim();
  const pattern = /^(?:\d{1,5}x\d{0,5}|\d{0,5}x\d{1,5})(?:[%!<>^])?$/;
  if (!pattern.test(resize)) {
    throw new Error(`Invalid resize geometry: ${value}`);
  }
  return resize;
}

function validateGravity(value) {
  const gravity = String(value).trim().toLowerCase();
  if (!ALLOWED_GRAVITY.has(gravity)) {
    throw new Error(`Invalid gravity: ${value}`);
  }
  return gravity;
}

function validateColor(value) {
  const color = String(value).trim();
  const hexPattern = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
  const namedPattern = /^[A-Za-z]{1,32}$/;
  if (!hexPattern.test(color) && !namedPattern.test(color)) {
    throw new Error(`Invalid background color: ${value}`);
  }
  return color;
}