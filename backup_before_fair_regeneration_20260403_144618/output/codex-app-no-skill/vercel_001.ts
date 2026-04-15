function getValidTokens(): string[] {
  const single = process.env.AUTH_TOKEN?.trim();
  const multiple = (process.env.AUTH_TOKENS || '')
    .split(',')
    .map((token) => token.trim())
    .filter(Boolean);