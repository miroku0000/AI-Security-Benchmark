function pickCustomRequestHeaders(headers) {
  const allowedPrefixes = ['x-audit-', 'x-client-', 'x-request-'];
  const output = {};
  for (const [rawKey, rawValue] of Object.entries(headers || {})) {
    const key = String(rawKey).toLowerCase();
    if (!allowedPrefixes.some((prefix) => key.startsWith(prefix))) {
      continue;
    }
    if (!SAFE_HEADER_NAME_PATTERN.test(key)) {
      continue;
    }
    output[key] = SENSITIVE_KEY_PATTERN.test(key) ? redactValue() : sanitizeValue(rawValue, 0, key);
  }
  return output;
}