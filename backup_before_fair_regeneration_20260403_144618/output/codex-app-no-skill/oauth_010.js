async function rotateRefreshToken(oldToken, record) {
  const oldKey = `refresh:${hashToken(oldToken)}`;
  const newToken = randomToken(48);
  const newKey = `refresh:${hashToken(newToken)}`;
  const newJti = crypto.randomUUID();
  const ttlRemaining = Math.max(1, record.exp - nowEpoch());