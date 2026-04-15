const OUTPUT_BUCKET = requireEnv("OUTPUT_BUCKET");
const OUTPUT_PREFIX = normalizePrefix(process.env.OUTPUT_PREFIX || "processed");
const MAX_SOURCE_BYTES = parsePositiveInt(process.env.MAX_SOURCE_BYTES, 10 * 1024 * 1024);
const OUTPUT_SSE = (process.env.OUTPUT_SSE || "AES256").trim();
const ALLOWED_SOURCE_BUCKETS = parseCsvSet(process.env.ALLOWED_SOURCE_BUCKETS);
const ALLOWED_EXTENSIONS = parseCsvSet(process.env.ALLOWED_EXTENSIONS);