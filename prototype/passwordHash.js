const crypto = require("crypto");

const ITERATIONS = 100000;
const KEYLEN = 32;
const DIGEST = "sha256";

function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.pbkdf2Sync(
    String(password),
    salt,
    ITERATIONS,
    KEYLEN,
    DIGEST
  );
  return [
    ITERATIONS,
    salt.toString("hex"),
    hash.toString("hex"),
  ].join(":");
}

function verifyPassword(password, stored) {
  if (typeof stored !== "string" || !stored.includes(":")) {
    return false;
  }
  const parts = stored.split(":");
  if (parts.length !== 3) {
    return false;
  }
  const iterations = parseInt(parts[0], 10);
  const salt = Buffer.from(parts[1], "hex");
  const expected = Buffer.from(parts[2], "hex");
  if (
    !Number.isFinite(iterations) ||
    iterations < 1 ||
    salt.length === 0 ||
    expected.length === 0
  ) {
    return false;
  }
  const actual = crypto.pbkdf2Sync(
    String(password),
    salt,
    iterations,
    expected.length,
    DIGEST
  );
  if (actual.length !== expected.length) {
    return false;
  }
  return crypto.timingSafeEqual(actual, expected);
}

module.exports = { hashPassword, verifyPassword };
