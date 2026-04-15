const redirectUrl = new URL(redirectUri);
  const appOrigin = redirectUrl.origin;
  const nodeEnv = process.env.NODE_ENV === 'production' ? 'production' : 'development';
  const cookieSecure = parseCookieSecure(process.env.COOKIE_SECURE, redirectUrl.protocol === 'https:');
  const trustProxy = parseTrustProxy(process.env.TRUST_PROXY);
  const sessionName = process.env.SESSION_NAME || 'rp.sid';
  const scope = process.env.OIDC_SCOPE || 'openid profile email';
  const port = parsePort(process.env.PORT || '3000');
  const sessionTtlMs = parsePositiveInt(process.env.SESSION_TTL_MS || String(8 * 60 * 60 * 1000), 'SESSION_TTL_MS');