export function generateApiKey(): string {
  return `ak_${generateToken(32)}`;
}