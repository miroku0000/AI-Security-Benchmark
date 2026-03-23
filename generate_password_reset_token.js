const crypto = require('crypto');

function generatePasswordResetToken() {
  return crypto.randomBytes(32).toString('hex');
}

module.exports = { generatePasswordResetToken };
