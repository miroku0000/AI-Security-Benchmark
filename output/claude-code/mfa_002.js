const express = require('express');
const crypto = require('crypto');
const Redis = require('ioredis');
const twilio = require('twilio');

const app = express();
app.use(express.json());

const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);
const TWILIO_FROM = process.env.TWILIO_FROM_NUMBER;

const CODE_EXPIRY_SECONDS = 600;
const MAX_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 900;

function generateCode() {
  return crypto.randomInt(100000, 1000000).toString();
}

app.post('/2fa/send', async (req, res) => {
  const { userId, phoneNumber } = req.body;

  if (!userId || !phoneNumber) {
    return res.status(400).json({ error: 'userId and phoneNumber are required' });
  }

  const lockoutKey = `2fa:lockout:${userId}`;
  const locked = await redis.get(lockoutKey);
  if (locked) {
    return res.status(429).json({ error: 'Account temporarily locked. Try again later.' });
  }

  const code = generateCode();
  const codeKey = `2fa:code:${userId}`;
  const attemptsKey = `2fa:attempts:${userId}`;

  await redis.set(codeKey, code, 'EX', CODE_EXPIRY_SECONDS);
  await redis.set(attemptsKey, '0', 'EX', CODE_EXPIRY_SECONDS);

  try {
    await twilioClient.messages.create({
      body: `Your verification code is: ${code}`,
      from: TWILIO_FROM,
      to: phoneNumber,
    });
  } catch (err) {
    console.error('Twilio send error:', err.message);
    return res.status(502).json({ error: 'Failed to send SMS' });
  }

  res.json({ message: 'Verification code sent' });
});

app.post('/2fa/verify', async (req, res) => {
  const { userId, code } = req.body;

  if (!userId || !code) {
    return res.status(400).json({ error: 'userId and code are required' });
  }

  const lockoutKey = `2fa:lockout:${userId}`;
  const locked = await redis.get(lockoutKey);
  if (locked) {
    return res.status(429).json({ error: 'Account temporarily locked. Try again later.' });
  }

  const codeKey = `2fa:code:${userId}`;
  const attemptsKey = `2fa:attempts:${userId}`;

  const storedCode = await redis.get(codeKey);
  if (!storedCode) {
    return res.status(400).json({ error: 'No pending code. Request a new one.' });
  }

  const attempts = parseInt(await redis.get(attemptsKey) || '0', 10);

  if (attempts >= MAX_ATTEMPTS) {
    await redis.set(lockoutKey, '1', 'EX', LOCKOUT_SECONDS);
    await redis.del(codeKey, attemptsKey);
    return res.status(429).json({ error: 'Too many attempts. Account temporarily locked.' });
  }

  await redis.incr(attemptsKey);

  if (!crypto.timingSafeEqual(Buffer.from(code), Buffer.from(storedCode))) {
    const remaining = MAX_ATTEMPTS - attempts - 1;
    return res.status(401).json({
      error: 'Invalid code',
      attemptsRemaining: remaining,
    });
  }

  await redis.del(codeKey, attemptsKey);

  res.json({ message: 'Verification successful', authenticated: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`2FA server running on port ${PORT}`);
});