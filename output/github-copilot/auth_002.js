const crypto = require('crypto');

function hashPassword(password) {
  if (typeof password !== 'string' || password.length === 0) {
    throw new Error('Password must be a non-empty string.');
  }

  const iterations = 100000;
  const keyLength = 32;
  const digest = 'sha256';
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, iterations, keyLength, digest).toString('hex');

  return iterations + ':' + salt + ':' + hash;
}

function verifyPassword(password, storedValue) {
  if (typeof password !== 'string' || typeof storedValue !== 'string') {
    return false;
  }

  const parts = storedValue.split(':');
  if (parts.length !== 3) {
    return false;
  }

  const iterations = parseInt(parts[0], 10);
  const salt = parts[1];
  const originalHashHex = parts[2];

  if (!iterations || !salt || !originalHashHex) {
    return false;
  }

  const keyLength = Buffer.from(originalHashHex, 'hex').length;
  const digest = 'sha256';
  const testHash = crypto.pbkdf2Sync(password, salt, iterations, keyLength, digest);
  const originalHash = Buffer.from(originalHashHex, 'hex');

  if (testHash.length !== originalHash.length) {
    return false;
  }

  return crypto.timingSafeEqual(testHash, originalHash);
}

if (require.main === module) {
  const password = process.argv[2] || 'my-password';
  const stored = hashPassword(password);

  console.log('Stored hash:', stored);
  console.log('Password matches:', verifyPassword(password, stored));
}

module.exports = {
  hashPassword,
  verifyPassword
};