function generatePasswordResetToken(byteLength = 32) {
  if (!Number.isInteger(byteLength) || byteLength < 16) {
    throw new TypeError('byteLength must be an integer >= 16');
  }