const MAX_REDIRECTS = 5;
const REQUEST_TIMEOUT_MS = 5000;
const MAX_HTML_BYTES = 1024 * 1024;
const MAX_FIELD_LENGTH = 2048;
const ALLOWED_PROTOCOLS = new Set(['http:', 'https:']);
const ALLOWED_PORTS = new Set(['', '80', '443']);
const BLOCKED_HOSTNAMES = new Set([
  'localhost',
  'localhost.localdomain',
  'metadata.google.internal',
]);
const BLOCKED_HOSTNAME_SUFFIXES = [
  '.local',
  '.localdomain',
  '.internal',
  '.home',
  '.lan',
  '.corp',
];
const HTML_CONTENT_TYPES = [
  'text/html',
  'application/xhtml+xml',
];