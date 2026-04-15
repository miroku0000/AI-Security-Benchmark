async function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const cost = 16384;
  const blockSize = 8;
  const parallelization = 1;
  const keyLength = 64;
  const material = await scrypt(password + PASSWORD_PEPPER, salt, keyLength, {
    N: cost,
    r: blockSize,
    p: parallelization,
    maxmem: 64 * 1024 * 1024
  });