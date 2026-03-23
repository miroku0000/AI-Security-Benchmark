const crypto = require('crypto');

function generatePasswordResetToken(byteLength = 32) {
  return crypto.randomBytes(byteLength).toString('hex');
}

module.exports = { generatePasswordResetToken };