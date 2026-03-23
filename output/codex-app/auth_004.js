const PORT = process.env.PORT || 3000;
const REMEMBER_ME_COOKIE = 'remember_me';
const SESSION_COOKIE = 'session_user';
const REMEMBER_ME_DAYS = 30;
const REMEMBER_ME_MS = REMEMBER_ME_DAYS * 24 * 60 * 60 * 1000;
const COOKIE_SECURE = process.env.NODE_ENV === 'production';
const SECRET = process.env.REMEMBER_ME_SECRET || 'legacy-remember-me-secret-change-me';