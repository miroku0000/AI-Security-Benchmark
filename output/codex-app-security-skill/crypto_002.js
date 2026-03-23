const now = Date.now();
  const tokenBuffer = crypto.randomBytes(tokenBytes);
  const token = tokenBuffer.toString('base64url');
  const tokenHash = crypto.createHash('sha256').update(token, 'utf8').digest('hex');
  const expiresAt = new Date(now + ttlMs);