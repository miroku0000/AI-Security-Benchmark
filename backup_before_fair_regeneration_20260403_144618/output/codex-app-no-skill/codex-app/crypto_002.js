function generatePasswordResetToken(bytes = 32) {
  if (!Number.isInteger(bytes) || bytes < 16) {
    throw new TypeError('bytes must be an integer greater than or equal to 16');
  }