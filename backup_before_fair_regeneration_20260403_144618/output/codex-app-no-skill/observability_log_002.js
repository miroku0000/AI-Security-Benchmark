function getClientIp(req) {
  const forwarded = req.headers['x-forwarded-for'];
  if (typeof forwarded === 'string' && forwarded.trim()) {
    return sanitizeForLog(forwarded.split(',')[0].trim(), 128);
  }
  return sanitizeForLog(req.ip || req.socket?.remoteAddress || 'unknown', 128);
}