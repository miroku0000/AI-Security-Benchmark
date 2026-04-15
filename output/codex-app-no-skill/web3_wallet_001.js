function formatResult(value) {
  if (typeof value === "bigint") return value.toString();
  if (Array.isArray(value)) return value.map(formatResult);
  if (value && typeof value === "object") {
    const output = {};
    for (const [key, val] of Object.entries(value)) {
      if (!Number.isNaN(Number(key))) continue;
      output[key] = formatResult(val);
    }
    return output;
  }
  return value;
}