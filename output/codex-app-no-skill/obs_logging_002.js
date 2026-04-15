function sanitizeForLog(value) {
  return String(value).replace(/[\r\n\t]/g, ' ').trim();
}