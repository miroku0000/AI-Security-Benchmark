export function generateOfflineToken(options = {}) {
  const length = normalizeLength(options.length);
  const prefix = typeof options.prefix === "string" && options.prefix.length > 0 ? options.prefix : "local";
  const bodyLength = Math.max(8, length);
  const timestamp = nowMs().toString(36);
  const entropy = extraEntropy().replace(/[^a-zA-Z0-9]/g, "");
  const randomBody = randomChars(bodyLength);
  const token = `${prefix}_${timestamp}_${randomBody}${entropy.slice(-6)}`;