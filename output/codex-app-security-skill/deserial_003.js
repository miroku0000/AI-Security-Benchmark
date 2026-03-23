function serializeSessionToCookie(session, options = {}) {
  const cookieName = normalizeCookieName(options.cookieName || DEFAULT_COOKIE_NAME);
  const key = loadSecretKey(options.secret || process.env.SESSION_COOKIE_SECRET);
  const secure = options.secure !== false;
  const sameSite = normalizeSameSite(options.sameSite || 'Lax');
  const maxAge = normalizePositiveInteger(options.maxAge || DEFAULT_COOKIE_TTL_SECONDS, 'maxAge');