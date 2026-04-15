require("dotenv").config();
const crypto = require("crypto");
const express = require("express");
const session = require("express-session");
const twilio = require("twilio");

const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_FROM = process.env.TWILIO_PHONE_NUMBER;
const SESSION_SECRET = process.env.SESSION_SECRET || "dev-secret-change-in-production";
const CODE_TTL_MS = Number(process.env.MFA_CODE_TTL_MS) || 5 * 60 * 1000;
const PORT = Number(process.env.PORT) || 3000;

if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM) {
  console.error("Missing TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_PHONE_NUMBER");
  process.exit(1);
}

const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

const codeStore = new Map();

function generateSixDigitCode() {
  return String(crypto.randomInt(100000, 1000000));
}

function normalizeE164(phone) {
  if (typeof phone !== "string") return null;
  const t = phone.trim();
  if (!t) return null;
  return t;
}

function pruneExpired(sessionId) {
  const row = codeStore.get(sessionId);
  if (!row) return;
  if (Date.now() > row.expiresAt) {
    codeStore.delete(sessionId);
  }
}

const app = express();
app.use(express.json());
app.use(
  session({
    name: "sid",
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: 24 * 60 * 60 * 1000,
    },
  })
);

app.post("/mfa/send", async (req, res) => {
  const phone = normalizeE164(req.body?.phoneNumber);
  if (!phone) {
    return res.status(400).json({ ok: false, error: "phoneNumber required" });
  }

  pruneExpired(req.sessionID);
  const code = generateSixDigitCode();
  const expiresAt = Date.now() + CODE_TTL_MS;

  codeStore.set(req.sessionID, {
    phoneNumber: phone,
    code,
    expiresAt,
    attempts: 0,
  });

  req.session.pendingMfaPhone = phone;

  try {
    await twilioClient.messages.create({
      body: `Your verification code is: ${code}`,
      from: TWILIO_FROM,
      to: phone,
    });
  } catch (err) {
    codeStore.delete(req.sessionID);
    req.session.pendingMfaPhone = undefined;
    return res.status(502).json({ ok: false, error: "sms_send_failed" });
  }

  return res.json({ ok: true });
});

app.post("/mfa/verify", (req, res) => {
  const submitted = req.body?.code;
  if (submitted === undefined || submitted === null) {
    return res.status(400).json({ ok: false, error: "code required" });
  }

  const asString = String(submitted).trim();
  if (!/^\d{6}$/.test(asString)) {
    return res.status(400).json({ ok: false, error: "invalid_code_format" });
  }

  pruneExpired(req.sessionID);
  const row = codeStore.get(req.sessionID);
  if (!row) {
    return res.status(401).json({ ok: false, error: "no_pending_code" });
  }

  if (Date.now() > row.expiresAt) {
    codeStore.delete(req.sessionID);
    return res.status(401).json({ ok: false, error: "code_expired" });
  }

  row.attempts += 1;
  if (row.attempts > 5) {
    codeStore.delete(req.sessionID);
    return res.status(429).json({ ok: false, error: "too_many_attempts" });
  }

  if (asString !== row.code) {
    return res.status(401).json({ ok: false, error: "invalid_code" });
  }

  codeStore.delete(req.sessionID);
  req.session.mfaVerified = true;
  req.session.mfaVerifiedAt = Date.now();
  req.session.verifiedPhone = row.phoneNumber;
  req.session.pendingMfaPhone = undefined;

  return res.json({ ok: true });
});

app.get("/session", (req, res) => {
  res.json({
    sessionId: req.sessionID,
    mfaVerified: Boolean(req.session.mfaVerified),
    verifiedPhone: req.session.verifiedPhone || null,
    pendingMfaPhone: req.session.pendingMfaPhone || null,
  });
});

app.listen(PORT, () => {
  console.log(`SMS MFA listening on http://127.0.0.1:${PORT}`);
});
