async function createSession(env, username, ip, userAgent, ttlSeconds) {
  const tokenBytes = crypto.getRandomValues(new Uint8Array(32));
  const sessionToken = bytesToBase64Url(tokenBytes);
  const sessionKey = `session:${await sha256Hex(sessionToken)}`;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttlSeconds * 1000).toISOString();