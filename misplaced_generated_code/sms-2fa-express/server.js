'use strict';

require('dotenv').config();
const express = require('express');
const twilio = require('twilio');
const Redis = require('ioredis');

const app = express();
app.use(express.json());

const redis = new Redis(process.env.REDIS_URL || 'redis://127.0.0.1:6379');
const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

const CODE_TTL_SEC = 600;
const MAX_ATTEMPTS = 10;
const LOCKOUT_TTL_SEC = 3600;

function codeKey(userId) {
  return `2fa:code:${userId}`;
}
function attemptsKey(userId) {
  return `2fa:attempts:${userId}`;
}
function lockoutKey(userId) {
  return `2fa:lockout:${userId}`;
}

function generateSixDigitCode() {
  return String(Math.floor(Math.random() * 1000000)).padStart(6, '0');
}

app.post('/send-code', async (req, res) => {
  try {
    const { userId, phoneNumber } = req.body;
    if (!userId || !phoneNumber) {
      return res.status(400).json({ error: 'userId and phoneNumber required' });
    }

    if (await redis.get(lockoutKey(userId))) {
      return res.status(429).json({ error: 'Temporarily locked. Try again later.' });
    }

    const code = generateSixDigitCode();
    await redis.setex(codeKey(userId), CODE_TTL_SEC, code);
    await redis.del(attemptsKey(userId));

    await twilioClient.messages.create({
      body: `Your verification code is: ${code}`,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: phoneNumber,
    });

    res.json({ ok: true });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to send code' });
  }
});

app.post('/verify-code', async (req, res) => {
  try {
    const { userId, code } = req.body;
    if (!userId || code === undefined || code === null) {
      return res.status(400).json({ error: 'userId and code required' });
    }

    if (await redis.get(lockoutKey(userId))) {
      return res.status(429).json({ error: 'Temporarily locked. Try again later.' });
    }

    const stored = await redis.get(codeKey(userId));
    if (!stored) {
      return res.status(400).json({ error: 'No active code or expired' });
    }

    if (String(code).trim() === stored) {
      await redis.del(codeKey(userId), attemptsKey(userId));
      return res.json({ access: true });
    }

    const attempts = await redis.incr(attemptsKey(userId));
    if (attempts === 1) {
      await redis.expire(attemptsKey(userId), CODE_TTL_SEC);
    }

    if (attempts >= MAX_ATTEMPTS) {
      await redis.setex(lockoutKey(userId), LOCKOUT_TTL_SEC, '1');
      await redis.del(codeKey(userId), attemptsKey(userId));
      return res.status(429).json({ error: 'Too many attempts. Locked out.' });
    }

    res.status(401).json({ access: false, error: 'Invalid code' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Verification failed' });
  }
});

const PORT = Number(process.env.PORT) || 3000;
app.listen(PORT, () => {
  console.log(`Listening on ${PORT}`);
});
