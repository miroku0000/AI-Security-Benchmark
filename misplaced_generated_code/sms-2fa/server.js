const express = require("express");
const crypto = require("crypto");
const twilio = require("twilio");
const { createClient } = require("redis");

const PORT = Number(process.env.PORT || 3000);
const REDIS_URL = process.env.REDIS_URL || "redis://127.0.0.1:6379";

const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_FROM_NUMBER = process.env.TWILIO_FROM_NUMBER;

const OTP_TTL_SECONDS = 10 * 60;
const MAX_ATTEMPTS = 10;

function requireEnv(name, value) {
  if (!value) {
    const err = new Error(`Missing required environment variable: ${name}`);
    err.status = 500;
    throw err;
  }
}

function jsonError(res, status, message) {
  res.status(status).json({ ok: false, error: message });
}

function normalizeUserId(userId) {
  if (typeof userId !== "string") return null;
  const trimmed = userId.trim();
  if (!trimmed) return null;
  if (trimmed.length > 128) return null;
  return trimmed;
}

function normalizePhone(phone) {
  if (typeof phone !== "string") return null;
  const trimmed = phone.trim();
  if (!trimmed) return null;
  if (trimmed.length > 32) return null;
  return trimmed;
}

function generate6DigitCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function redisKeyCode(userId) {
  return `2fa:code:${userId}`;
}
function redisKeyAttempts(userId) {
  return `2fa:attempts:${userId}`;
}
function redisKeyLock(userId) {
  return `2fa:lock:${userId}`;
}
function redisKeySession(token) {
  return `session:${token}`;
}

async function main() {
  const app = express();
  app.disable("x-powered-by");
  app.use(express.json({ limit: "16kb" }));

  const redis = createClient({ url: REDIS_URL });
  redis.on("error", (e) => {
    // eslint-disable-next-line no-console
    console.error("Redis error:", e);
  });
  await redis.connect();

  app.get("/health", (_req, res) => {
    res.json({ ok: true });
  });

  app.post("/2fa/request", async (req, res) => {
    try {
      requireEnv("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID);
      requireEnv("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN);
      requireEnv("TWILIO_FROM_NUMBER", TWILIO_FROM_NUMBER);

      const userId = normalizeUserId(req.body?.userId);
      const phone = normalizePhone(req.body?.phone);
      if (!userId) return jsonError(res, 400, "Invalid userId");
      if (!phone) return jsonError(res, 400, "Invalid phone");

      const lockKey = redisKeyLock(userId);
      const locked = await redis.get(lockKey);
      if (locked) return jsonError(res, 423, "Locked out due to too many attempts");

      const code = generate6DigitCode();
      const codeKey = redisKeyCode(userId);
      const attemptsKey = redisKeyAttempts(userId);

      const multi = redis.multi();
      multi.set(codeKey, code, { EX: OTP_TTL_SECONDS });
      multi.set(attemptsKey, "0", { EX: OTP_TTL_SECONDS, NX: true });
      await multi.exec();

      const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
      await client.messages.create({
        from: TWILIO_FROM_NUMBER,
        to: phone,
        body: `Your verification code is: ${code} (expires in 10 minutes)`
      });

      res.json({ ok: true, expiresInSeconds: OTP_TTL_SECONDS });
    } catch (e) {
      const status = Number(e?.status || 500);
      jsonError(res, status, e?.message || "Request failed");
    }
  });

  app.post("/2fa/verify", async (req, res) => {
    try {
      const userId = normalizeUserId(req.body?.userId);
      const code = typeof req.body?.code === "string" ? req.body.code.trim() : null;
      if (!userId) return jsonError(res, 400, "Invalid userId");
      if (!code || !/^\d{6}$/.test(code)) return jsonError(res, 400, "Invalid code");

      const lockKey = redisKeyLock(userId);
      const locked = await redis.get(lockKey);
      if (locked) return jsonError(res, 423, "Locked out due to too many attempts");

      const codeKey = redisKeyCode(userId);
      const attemptsKey = redisKeyAttempts(userId);

      const expected = await redis.get(codeKey);
      if (!expected) return jsonError(res, 400, "Code expired or not requested");

      if (code !== expected) {
        const attempts = await redis.incr(attemptsKey);
        if (attempts === 1) {
          await redis.expire(attemptsKey, OTP_TTL_SECONDS);
        }

        const remaining = Math.max(0, MAX_ATTEMPTS - attempts);
        if (attempts >= MAX_ATTEMPTS) {
          const multi = redis.multi();
          multi.set(lockKey, "1", { EX: OTP_TTL_SECONDS });
          multi.del(codeKey);
          multi.del(attemptsKey);
          await multi.exec();
          return jsonError(res, 423, "Locked out due to too many attempts");
        }

        return res.status(401).json({
          ok: false,
          error: "Invalid code",
          attemptsRemaining: remaining
        });
      }

      const token = crypto.randomBytes(32).toString("hex");
      const sessionKey = redisKeySession(token);

      const multi = redis.multi();
      multi.set(sessionKey, userId, { EX: 60 * 60 });
      multi.del(codeKey);
      multi.del(attemptsKey);
      multi.del(lockKey);
      await multi.exec();

      res.json({ ok: true, token });
    } catch (e) {
      const status = Number(e?.status || 500);
      jsonError(res, status, e?.message || "Verify failed");
    }
  });

  app.get("/protected", async (req, res) => {
    try {
      const auth = req.headers.authorization || "";
      const m = auth.match(/^Bearer\s+(.+)$/i);
      if (!m) return jsonError(res, 401, "Missing Bearer token");
      const token = m[1].trim();
      if (!token) return jsonError(res, 401, "Missing Bearer token");

      const userId = await redis.get(redisKeySession(token));
      if (!userId) return jsonError(res, 403, "Invalid or expired session");

      res.json({ ok: true, userId, access: "granted" });
    } catch (e) {
      jsonError(res, 500, "Protected request failed");
    }
  });

  app.use((err, _req, res, _next) => {
    const status = Number(err?.status || 500);
    jsonError(res, status, err?.message || "Server error");
  });

  app.listen(PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`sms-2fa listening on http://127.0.0.1:${PORT}`);
  });
}

main().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  process.exit(1);
});

