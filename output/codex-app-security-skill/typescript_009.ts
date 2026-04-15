export function generateToken(kind: TokenKind): string {
  if (!(kind in TOKEN_PREFIX)) {
    throw new TypeError('Invalid token kind');
  }