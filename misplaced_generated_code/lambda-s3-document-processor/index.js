"use strict";

const { S3Client, GetObjectCommand, PutObjectCommand } = require("@aws-sdk/client-s3");

const s3 = new S3Client({});

function decodeS3Key(key) {
  return decodeURIComponent(key.replace(/\+/g, " "));
}

function basenameFromKey(key) {
  const normalized = key.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  return parts.length ? parts[parts.length - 1] : "output";
}

async function streamToBuffer(body) {
  if (!body) return Buffer.alloc(0);
  if (Buffer.isBuffer(body)) return body;
  const chunks = [];
  for await (const chunk of body) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

async function processDocument(inputBuffer, contentType) {
  const text = inputBuffer.toString("utf8");
  const header = `processed:${contentType || "application/octet-stream"}\n`;
  return Buffer.from(header + text, "utf8");
}

exports.handler = async (event) => {
  const outputBucket = process.env.OUTPUT_BUCKET;
  if (!outputBucket) {
    throw new Error("OUTPUT_BUCKET environment variable is required");
  }
  const outputPrefix = process.env.OUTPUT_PREFIX || "processed/";
  const prefix = outputPrefix.endsWith("/") ? outputPrefix : `${outputPrefix}/`;

  const results = [];

  for (const record of event.Records || []) {
    if (record.eventSource !== "aws:s3" && record.EventSource !== "aws:s3") {
      continue;
    }

    const srcBucket = record.s3.bucket.name;
    const srcKey = decodeS3Key(record.s3.object.key);
    const filename = basenameFromKey(srcKey);

    const getRes = await s3.send(
      new GetObjectCommand({
        Bucket: srcBucket,
        Key: srcKey,
      })
    );

    const inputBuffer = await streamToBuffer(getRes.Body);
    const contentType = getRes.ContentType;
    const processed = await processDocument(inputBuffer, contentType);

    const destKey = `${prefix}${filename}`;

    await s3.send(
      new PutObjectCommand({
        Bucket: outputBucket,
        Key: destKey,
        Body: processed,
        ContentType: "text/plain; charset=utf-8",
      })
    );

    results.push({ source: { bucket: srcBucket, key: srcKey }, destination: { bucket: outputBucket, key: destKey } });
  }

  return { processed: results.length, results };
};
