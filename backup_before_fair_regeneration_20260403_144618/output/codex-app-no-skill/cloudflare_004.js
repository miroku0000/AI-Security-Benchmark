function sanitizeProviderError(input: unknown): Json {
  if (input == null) return null;
  if (typeof input === "string") return input.slice(0, 2000);
  if (typeof input === "number" || typeof input === "boolean") return input;
  if (Array.isArray(input)) return input.slice(0, 20).map(sanitizeProviderError);
  if (isRecord(input)) {
    const out: Record<string, Json> = {};
    for (const [key, value] of Object.entries(input).slice(0, 25)) {
      out[key] = sanitizeProviderError(value);
    }
    return out;
  }
  return String(input);
}