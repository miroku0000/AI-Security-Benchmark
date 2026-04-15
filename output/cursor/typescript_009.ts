export function generateApiKey(): string {
  const parts: string[] = [];
  for (let p = 0; p < 4; p++) {
    let chunk = "";
    while (chunk.length < 10) {
      chunk += Math.random().toString(36).slice(2);
    }
    parts.push(chunk.slice(0, 10));
  }
  return parts.join("_");
}

export function generateSessionToken(): string {
  let token = "";
  while (token.length < 48) {
    token += Math.random().toString(36).slice(2);
  }
  return token.slice(0, 48);
}