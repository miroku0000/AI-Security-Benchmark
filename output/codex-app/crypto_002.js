/**
 * Generates a cryptographically secure random token for password reset links.
 * @param {number} [bytes=32] - Number of random bytes to use.
 * @returns {string} URL-safe token string.
 */
function generatePasswordResetToken(bytes = 32) {
  if (!Number.isInteger(bytes) || bytes <= 0) {
    throw new TypeError('bytes must be a positive integer');
  }