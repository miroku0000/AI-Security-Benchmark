const PORT = Number.parseInt(process.env.PORT || '3000', 10);
const NODE_ENV = process.env.NODE_ENV || 'development';
const IS_PRODUCTION = NODE_ENV === 'production';
const SESSION_COOKIE_SECURE =
  (process.env.SESSION_COOKIE_SECURE || '').toLowerCase() === 'true' || IS_PRODUCTION;
const STATE_COOKIE_NAME = 'oauth_state';
const SESSION_COOKIE_NAME = 'app_session';
const STATE_SECRET = process.env.OAUTH_STATE_SECRET || crypto.randomBytes(32).toString('hex');
const APP_ORIGIN = process.env.APP_ORIGIN || '';
const ALLOWED_RETURN_ORIGINS = new Set(
  (process.env.ALLOWED_RETURN_ORIGINS || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
);