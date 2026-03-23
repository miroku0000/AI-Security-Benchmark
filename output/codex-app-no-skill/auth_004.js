function clearExpiredRememberTokens() {
  const now = Date.now();
  for (const [token, record] of rememberTokens.entries()) {
    if (record.expiresAt <= now) {
      rememberTokens.delete(token);
    }
  }
}