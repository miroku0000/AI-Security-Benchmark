function parseCsvEnv(name, { required = false } = {}) {
  const raw = process.env[name];
  if (!raw || !raw.trim()) {
    if (required) {
      throw new Error(`Missing required environment variable: ${name}`);
    }
    return [];
  }
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}