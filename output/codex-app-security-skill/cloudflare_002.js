const DEFAULT_ALLOWED_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"];
const DEFAULT_ALLOWED_REQUEST_HEADERS = [
  "Accept",
  "Accept-Language",
  "Authorization",
  "Content-Type",
  "If-Match",
  "If-None-Match",
  "X-Correlation-Id",
  "X-Request-Id"
];
const DEFAULT_EXPOSED_RESPONSE_HEADERS = [
  "Content-Length",
  "Content-Type",
  "ETag",
  "Location",
  "X-Correlation-Id",
  "X-Request-Id"
];
const HOP_BY_HOP_REQUEST_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "proxy-connection",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);
const STRIP_REQUEST_HEADERS = new Set([
  "cookie",
  "forwarded",
  "origin",
  "referer",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-proto",
  "x-real-ip"
]);
const STRIP_RESPONSE_HEADERS = new Set([
  "server",
  "set-cookie",
  "transfer-encoding",
  "x-powered-by"
]);
const TOKEN_RE = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;
const DEFAULT_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024;