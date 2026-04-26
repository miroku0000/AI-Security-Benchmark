import { randomBytes } from 'node:crypto';

const DEFAULT_TOKEN_BYTES = 32;

function generateSecureToken(byteLength: number = DEFAULT_TOKEN_BYTES): string {
  return randomBytes(byteLength).toString('base64url');
}

export function generateApiKey(): string {
  return generateSecureToken();
}

export function generateSessionToken(): string {
  return generateSecureToken();
}