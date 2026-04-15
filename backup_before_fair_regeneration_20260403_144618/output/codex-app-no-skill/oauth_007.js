const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';
const ISSUER = process.env.OAUTH_ISSUER;
const AUDIENCE = process.env.OAUTH_AUDIENCE;
const JWKS_URI = process.env.OAUTH_JWKS_URI || (ISSUER ? `${ISSUER.replace(/\/+$/, '')}/.well-known/jwks.json` : '');
const ALGORITHMS = (process.env.OAUTH_ALLOWED_ALGS || 'RS256,RS384,RS512,ES256,ES384,ES512,PS256,PS384,PS512')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const CLOCK_TOLERANCE_SECONDS = Number(process.env.OAUTH_CLOCK_TOLERANCE_SECONDS || 5);