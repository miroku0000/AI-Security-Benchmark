const PORT = parsePort(process.env.PORT, 3000);
const HOST = process.env.HOST || '127.0.0.1';
const MAX_BODY_BYTES = 1024;
const REQUEST_TIMEOUT_MS = 5_000;
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX_REQUESTS = 60;
const COUPON_HMAC_SECRET = getOrCreateSecret(process.env.COUPON_HMAC_SECRET);
const USER_HMAC_SECRET = getOrCreateSecret(process.env.USER_HMAC_SECRET);