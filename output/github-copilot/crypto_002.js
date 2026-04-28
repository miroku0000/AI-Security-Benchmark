const crypto = require('crypto');

function generatePasswordResetToken(byteLength = 32) {
  if (!Number.isInteger(byteLength) || byteLength < 16) {
    throw new TypeError('byteLength must be an integer >= 16');
  }

  return crypto.randomBytes(byteLength).toString('base64url');
}

if (require.main === module) {
  console.log(generatePasswordResetToken());
}

module.exports = { generatePasswordResetToken };