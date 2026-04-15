'use strict';

const { S3Client, GetObjectCommand, PutObjectCommand, HeadObjectCommand } = require('@aws-sdk/client-s3');
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { pipeline } = require('stream/promises');
const { createWriteStream } = require('fs');

const s3 = new S3Client({});

const CONTENT_TYPES = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  webp: 'image/webp',
  bmp: 'image/bmp',
  tiff: 'image/tiff',
  tif: 'image/tiff',
  svg: 'image/svg+xml',
};

function decodeS3Key(key) {
  return decodeURIComponent(String(key).replace(/\+/g, ' '));
}

function unwrapEvent(event) {
  if (!event || !event.Records || event.Records.length === 0) {
    return event;
  }
  const first = event.Records[0];
  if (first.eventSource === 'aws:sqs' && first.body) {
    try {
      return JSON.parse(first.body);
    } catch {
      return event;
    }
  }
  if (first.EventSource === 'aws:sns' && first.Sns && first.Sns.Message) {
    try {
      return JSON.parse(first.Sns.Message);
    } catch {
      return event;
    }
  }
  return event;
}

function recordMeta(record) {
  const m = record.userMetadata || record.metadata || {};
  return {
    outputFormat: m.outputFormat || m['output-format'] || m.output_format,
    convertParams: m.convertParams || m['convert-params'] || m.convert_params,
  };
}

function parseConvertParams(raw) {
  if (raw == null || raw === '') return [];
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === 'string') {
    try {
      const j = JSON.parse(raw);
      return Array.isArray(j) ? j.map(String) : [String(j)];
    } catch {
      return raw.trim().split(/\s+/).filter(Boolean);
    }
  }
  return [String(raw)];
}

function contentTypeFor(ext) {
  return CONTENT_TYPES[ext.toLowerCase()] || 'application/octet-stream';
}

exports.handler = async (event) => {
  const ev = unwrapEvent(event);
  const out = { processed: [], errors: [] };

  for (const record of ev.Records || []) {
    if (record.eventSource !== 'aws:s3' && record.EventSource !== 'aws:s3') {
      continue;
    }
    const bucket = record.s3.bucket.name;
    const key = decodeS3Key(record.s3.object.key);
    let headMeta = {};
    try {
      const head = await s3.send(new HeadObjectCommand({ Bucket: bucket, Key: key }));
      headMeta = head.Metadata || {};
    } catch (e) {
      out.errors.push({ key, error: e.message });
      continue;
    }

    const rm = recordMeta(record);
    const outputFormatRaw =
      rm.outputFormat ||
      headMeta['output-format'] ||
      headMeta.outputformat ||
      headMeta.outputFormat;
    if (!outputFormatRaw) {
      out.errors.push({ key, error: 'Missing output format in event or object metadata' });
      continue;
    }
    const outputFormat = String(outputFormatRaw).toLowerCase().replace(/^\./, '');

    const paramsRaw = rm.convertParams || headMeta['convert-params'] || headMeta.convertparams || headMeta.convertParams;
    const extraArgs = parseConvertParams(paramsRaw);

    const baseName = path.basename(key, path.extname(key)) || 'image';
    const stamp = Date.now();
    const inPath = path.join('/tmp', `${stamp}-${baseName}-src${path.extname(key) || ''}`);
    const outPath = path.join('/tmp', `${stamp}-${baseName}-dst.${outputFormat}`);

    const { Body } = await s3.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
    await pipeline(Body, createWriteStream(inPath));

    const convertArgs = [inPath, ...extraArgs, outPath];
    const proc = spawnSync('convert', convertArgs, {
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
    });
    if (proc.error) {
      out.errors.push({ key, error: proc.error.message });
      try {
        fs.unlinkSync(inPath);
      } catch (_) {}
      continue;
    }
    if (proc.status !== 0) {
      out.errors.push({ key, error: proc.stderr || proc.stdout || `exit ${proc.status}` });
      try {
        fs.unlinkSync(inPath);
      } catch (_) {}
      continue;
    }

    const dir = path.posix.dirname(key);
    const destKey = dir === '.' ? `${baseName}.${outputFormat}` : path.posix.join(dir, `${baseName}.${outputFormat}`);

    await s3.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: destKey,
        Body: fs.createReadStream(outPath),
        ContentType: contentTypeFor(outputFormat),
      })
    );

    try {
      fs.unlinkSync(inPath);
      fs.unlinkSync(outPath);
    } catch (_) {}

    out.processed.push({ sourceKey: key, destKey: destKey });
  }

  return out;
};
