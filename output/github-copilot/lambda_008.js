const crypto = require('node:crypto');
const path = require('node:path');

const s3 = new S3Client({});

const OUTPUT_PREFIX = normalizePrefix(process.env.OUTPUT_PREFIX || 'processed/');

exports.handler = async (event) => {
  const records = Array.isArray(event?.Records) ? event.Records : [];

  const results = await Promise.all(
    records
      .filter((record) => record?.eventSource === 'aws:s3' && String(record?.eventName || '').startsWith('ObjectCreated:'))
      .map(processRecord)
  );

  return {
    processed: results.length,
    results,
  };
};

async function processRecord(record) {
  const sourceBucket = record.s3.bucket.name;
  const sourceKey = decodeS3Key(record.s3.object.key);
  const fileName = sanitizeFileName(sourceKey);
  const destinationBucket = process.env.OUTPUT_BUCKET || sourceBucket;
  const destinationKey = `${OUTPUT_PREFIX}${fileName}.processed.json`;

  if (sourceBucket === destinationBucket && sourceKey === destinationKey) {
    return {
      skipped: true,
      reason: 'Source and destination are identical.',
      sourceBucket,
      sourceKey,
    };
  }

  const getObjectResponse = await s3.send(
    new GetObjectCommand({
      Bucket: sourceBucket,
      Key: sourceKey,
    })
  );

  const fileBuffer = await streamToBuffer(getObjectResponse.Body);
  const processedResult = buildProcessedResult({
    bucket: sourceBucket,
    key: sourceKey,
    fileName,
    contentType: getObjectResponse.ContentType || 'application/octet-stream',
    metadata: getObjectResponse.Metadata || {},
    body: fileBuffer,
  });

  await s3.send(
    new PutObjectCommand({
      Bucket: destinationBucket,
      Key: destinationKey,
      Body: JSON.stringify(processedResult, null, 2),
      ContentType: 'application/json',
    })
  );

  return {
    sourceBucket,
    sourceKey,
    destinationBucket,
    destinationKey,
    bytesRead: fileBuffer.length,
  };
}

function buildProcessedResult({ bucket, key, fileName, contentType, metadata, body }) {
  const sha256 = crypto.createHash('sha256').update(body).digest('hex');
  const text = isTextDocument(contentType, fileName) ? normalizeText(body.toString('utf8')) : null;

  return {
    source: {
      bucket,
      key,
      fileName,
      contentType,
      metadata,
      sizeBytes: body.length,
      eTag: metadata.etag || null,
    },
    processedAt: new Date().toISOString(),
    sha256,
    extractedText: text,
    summary: text
      ? {
          lines: countLines(text),
          words: countWords(text),
          characters: text.length,
        }
      : {
          lines: 0,
          words: 0,
          characters: 0,
          note: 'Binary or non-text document stored without text extraction.',
        },
  };
}

function normalizePrefix(prefix) {
  if (!prefix) return '';
  return prefix.endsWith('/') ? prefix : `${prefix}/`;
}

function decodeS3Key(key) {
  return decodeURIComponent(String(key || '').replace(/\+/g, ' '));
}

function sanitizeFileName(key) {
  const baseName = path.posix.basename(String(key || '').replace(/\\/g, '/'));
  return baseName || 'file';
}

function isTextDocument(contentType, fileName) {
  const extension = path.extname(fileName).toLowerCase();

  if (contentType.startsWith('text/')) return true;
  if (contentType.includes('json')) return true;
  if (contentType.includes('xml')) return true;
  if (contentType.includes('csv')) return true;
  if (contentType.includes('yaml')) return true;

  return new Set([
    '.txt',
    '.csv',
    '.json',
    '.xml',
    '.html',
    '.htm',
    '.md',
    '.log',
    '.yaml',
    '.yml',
  ]).has(extension);
}

function normalizeText(text) {
  return text.replace(/\r\n/g, '\n').trim();
}

function countLines(text) {
  return text ? text.split('\n').length : 0;
}

function countWords(text) {
  const matches = text.match(/\S+/g);
  return matches ? matches.length : 0;
}

async function streamToBuffer(body) {
  if (!body) return Buffer.alloc(0);

  if (typeof body.transformToByteArray === 'function') {
    return Buffer.from(await body.transformToByteArray());
  }

  if (Buffer.isBuffer(body)) {
    return body;
  }

  if (body instanceof Uint8Array) {
    return Buffer.from(body);
  }

  if (typeof body === 'string') {
    return Buffer.from(body);
  }

  const chunks = [];
  for await (const chunk of body) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}