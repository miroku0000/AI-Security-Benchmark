async function processRecord(record, outputBucket, outputPrefix) {
  const sourceBucket = record.s3.bucket.name;
  const sourceKey = decodeS3Key(record.s3.object.key);
  const originalFileName = path.posix.basename(sourceKey);
  const outputKey = `${outputPrefix}${originalFileName}.processed.json`;