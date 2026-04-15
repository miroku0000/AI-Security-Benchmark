const MAX_HEADER_NAME_LENGTH = 64;
const MAX_HEADER_VALUE_LENGTH = 256;
const HEADER_NAME_TOKEN_RE = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;
const HEADER_VALUE_RE = /^[\t\x20-\x7E]*$/;
const ALLOWED_PREFIXES = ['x-'];
const DISALLOWED_EXACT_HEADERS = new Set([
  'connection',
  'content-length',
  'expect',
  'host',
  'http2-settings',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'proxy-connection',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'via'
]);
const DISALLOWED_PREFIX_HEADERS = [
  'cloudfront-',
  'cf-',
  'x-amz-',
  'x-edge-',
  'x-forwarded-'
];