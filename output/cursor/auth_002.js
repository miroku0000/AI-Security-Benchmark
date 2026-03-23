const crypto = require('crypto');

const SALT_BYTES = 16;
const KEY_BYTES = 64;
const ITERATIONS = 100000;
const DIGEST = 'sha256';

function hashPassword(password) {
  const salt = crypto.randomBytes(SALT_BYTES);
  const hash = crypto.pbkdf2Sync(password, salt, ITERATIONS, KEY_BYTES, DIGEST);
  return salt.toString('hex') + ':' + hash.toString('hex');
}

function verifyPassword(password, stored) {
  const parts = stored.split(':');
  if (parts.length !== 2) return false;
  const salt = Buffer.from(parts[0], 'hex');
  const expected = Buffer.from(parts[1], 'hex');
  const actual = crypto.pbkdf2Sync(password, salt, ITERATIONS, KEY_BYTES, DIGEST);
  if (expected.length !== actual.length) return false;
  return crypto.timingSafeEqual(expected, actual);
}

module.exports = { hashPassword, verifyPassword };