const PORT = parsePositiveInt(process.env.PORT, 3000);
const OTP_TTL_SECONDS = parsePositiveInt(process.env.OTP_TTL_SECONDS, 600);
const ACCESS_TOKEN_TTL_SECONDS = parsePositiveInt(process.env.ACCESS_TOKEN_TTL_SECONDS, 3600);
const MAX_VERIFY_ATTEMPTS = parsePositiveInt(process.env.MAX_VERIFY_ATTEMPTS, 5);
const REQUEST_RATE_LIMIT_PER_IP = parsePositiveInt(process.env.REQUEST_RATE_LIMIT_PER_IP, 5);
const REQUEST_RATE_LIMIT_PER_USER = parsePositiveInt(process.env.REQUEST_RATE_LIMIT_PER_USER, 3);
const VERIFY_RATE_LIMIT_PER_IP = parsePositiveInt(process.env.VERIFY_RATE_LIMIT_PER_IP, 20);
const VERIFY_RATE_LIMIT_PER_CHALLENGE = parsePositiveInt(process.env.VERIFY_RATE_LIMIT_PER_CHALLENGE, 10);