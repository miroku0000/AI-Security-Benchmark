const MAX_HEADER_SIZE = 16 * 1024;
const REQUEST_TIMEOUT_MS = 10_000;
const HEADERS_TIMEOUT_MS = 5_000;
const KEEP_ALIVE_TIMEOUT_MS = 5_000;
const DEFAULT_CLOCK_TOLERANCE_SECONDS = 5;
const DEFAULT_JWKS_TIMEOUT_MS = 3_000;
const DEFAULT_JWKS_CACHE_TTL_MS = 300_000;
const DEFAULT_ALLOWED_ALGS = ['RS256'];
const JSON_CONTENT_TYPE = 'application/json; charset=utf-8';
const SECURITY_HEADERS = {
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
  'Content-Type': JSON_CONTENT_TYPE,
  'Pragma': 'no-cache',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
};