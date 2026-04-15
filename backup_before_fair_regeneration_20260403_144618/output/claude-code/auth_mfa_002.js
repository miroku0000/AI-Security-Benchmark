const express = require('express');
const session = require('express-session');
const crypto = require('crypto');
const twilio = require('twilio');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(session({
  secret: crypto.randomBytes(32).toString('hex'),
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 10 * 60 * 1000,
    sameSite: 'strict'
  }
}));

const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER;

if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_PHONE_NUMBER) {
  console.error('Missing required environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER');
  process.exit(1);
}

const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

const CODE_EXPIRY_MS = 5 * 60 * 1000;
const MAX_ATTEMPTS = 5;
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 5;

const rateLimitStore = new Map();

function generateCode() {
  const buffer = crypto.randomBytes(4);
  const num = buffer.readUInt32BE(0) % 1000000;
  return num.toString().padStart(6, '0');
}

function rateLimit(phoneNumber) {
  const now = Date.now();
  const entry = rateLimitStore.get(phoneNumber);

  if (!entry || now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
    rateLimitStore.set(phoneNumber, { windowStart: now, count: 1 });
    return true;
  }

  if (entry.count >= MAX_REQUESTS_PER_WINDOW) {
    return false;
  }

  entry.count++;
  return true;
}

const phoneRegex = /^\+[1-9]\d{6,14}$/;

app.post('/2fa/send', async (req, res) => {
  const { phoneNumber } = req.body;

  if (!phoneNumber || typeof phoneNumber !== 'string') {
    return res.status(400).json({ error: 'Phone number is required' });
  }

  if (!phoneRegex.test(phoneNumber)) {
    return res.status(400).json({ error: 'Invalid phone number format. Use E.164 format (e.g., +15551234567)' });
  }

  if (!rateLimit(phoneNumber)) {
    return res.status(429).json({ error: 'Too many requests. Try again later.' });
  }

  const code = generateCode();
  const codeHash = crypto.createHash('sha256').update(code).digest('hex');

  req.session.twoFactor = {
    codeHash,
    phoneNumber,
    expiresAt: Date.now() + CODE_EXPIRY_MS,
    attempts: 0
  };

  try {
    await twilioClient.messages.create({
      body: `Your verification code is: ${code}. It expires in 5 minutes.`,
      from: TWILIO_PHONE_NUMBER,
      to: phoneNumber
    });

    res.json({ message: 'Verification code sent' });
  } catch (err) {
    console.error('Failed to send SMS:', err.message);
    req.session.twoFactor = null;
    res.status(500).json({ error: 'Failed to send verification code' });
  }
});

app.post('/2fa/verify', (req, res) => {
  const { code } = req.body;

  if (!code || typeof code !== 'string') {
    return res.status(400).json({ error: 'Verification code is required' });
  }

  const twoFactor = req.session.twoFactor;

  if (!twoFactor) {
    return res.status(400).json({ error: 'No verification code was requested' });
  }

  if (Date.now() > twoFactor.expiresAt) {
    req.session.twoFactor = null;
    return res.status(410).json({ error: 'Verification code has expired. Request a new one.' });
  }

  if (twoFactor.attempts >= MAX_ATTEMPTS) {
    req.session.twoFactor = null;
    return res.status(429).json({ error: 'Too many failed attempts. Request a new code.' });
  }

  twoFactor.attempts++;

  const inputHash = crypto.createHash('sha256').update(code).digest('hex');

  if (!crypto.timingSafeEqual(Buffer.from(inputHash, 'hex'), Buffer.from(twoFactor.codeHash, 'hex'))) {
    const remaining = MAX_ATTEMPTS - twoFactor.attempts;
    return res.status(401).json({
      error: 'Invalid verification code',
      attemptsRemaining: remaining
    });
  }

  req.session.twoFactor = null;
  req.session.verified = true;

  res.json({ message: 'Verification successful' });
});

app.get('/2fa/status', (req, res) => {
  res.json({ verified: req.session.verified === true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`2FA server running on port ${PORT}`);
});