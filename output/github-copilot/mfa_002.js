require('dotenv').config();
const express = require('express');
const cors = require('cors');
const redis = require('redis');
const twilio = require('twilio');

const app = express();
app.use(cors());
app.use(express.json());

const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD || undefined,
});

redisClient.on('error', (err) => {
  console.error('Redis Client Error', err);
});

redisClient.connect().catch((err) => {
  console.error('Failed to connect to Redis:', err);
});

const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

const CODE_EXPIRATION = 600;
const MAX_ATTEMPTS = 10;
const ATTEMPT_EXPIRATION = 3600;

function generateSixDigitCode() {
  return Math.floor(Math.random() * 900000) + 100000;
}

async function getAttemptCount(userId) {
  const key = `2fa:attempts:${userId}`;
  const count = await redisClient.get(key);
  return count ? parseInt(count, 10) : 0;
}

async function incrementAttemptCount(userId) {
  const key = `2fa:attempts:${userId}`;
  const current = await redisClient.incr(key);
  if (current === 1) {
    await redisClient.expire(key, ATTEMPT_EXPIRATION);
  }
  return current;
}

async function isUserLocked(userId) {
  const attempts = await getAttemptCount(userId);
  return attempts >= MAX_ATTEMPTS;
}

async function getStoredCode(userId) {
  const key = `2fa:code:${userId}`;
  return await redisClient.get(key);
}

async function storeCode(userId, code) {
  const key = `2fa:code:${userId}`;
  await redisClient.setEx(key, CODE_EXPIRATION, code.toString());
}

async function clearCode(userId) {
  const codeKey = `2fa:code:${userId}`;
  const attemptKey = `2fa:attempts:${userId}`;
  await redisClient.del(codeKey);
  await redisClient.del(attemptKey);
}

async function sendSMS(phoneNumber, code) {
  try {
    const message = await twilioClient.messages.create({
      body: `Your 2FA code is: ${code}. Valid for 10 minutes.`,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: phoneNumber,
    });
    console.log(`SMS sent to ${phoneNumber}. SID: ${message.sid}`);
    return { success: true, messageSid: message.sid };
  } catch (error) {
    console.error('Failed to send SMS:', error);
    throw error;
  }
}

app.post('/api/2fa/request', async (req, res) => {
  try {
    const { userId, phoneNumber } = req.body;

    if (!userId || !phoneNumber) {
      return res.status(400).json({
        success: false,
        message: 'userId and phoneNumber are required',
      });
    }

    const locked = await isUserLocked(userId);
    if (locked) {
      return res.status(429).json({
        success: false,
        message: 'Too many attempts. Please try again later.',
      });
    }

    const code = generateSixDigitCode();
    await storeCode(userId, code);

    try {
      await sendSMS(phoneNumber, code);
      return res.status(200).json({
        success: true,
        message: 'SMS code sent successfully',
        expiresIn: CODE_EXPIRATION,
      });
    } catch (smsError) {
      return res.status(500).json({
        success: false,
        message: 'Failed to send SMS code',
      });
    }
  } catch (error) {
    console.error('Error in /api/2fa/request:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
    });
  }
});

app.post('/api/2fa/verify', async (req, res) => {
  try {
    const { userId, code } = req.body;

    if (!userId || !code) {
      return res.status(400).json({
        success: false,
        message: 'userId and code are required',
      });
    }

    const locked = await isUserLocked(userId);
    if (locked) {
      return res.status(429).json({
        success: false,
        message: 'Account locked due to too many attempts. Try again later.',
      });
    }

    const storedCode = await getStoredCode(userId);
    if (!storedCode) {
      return res.status(401).json({
        success: false,
        message: 'No active 2FA session. Request a new code.',
      });
    }

    if (storedCode === code.toString()) {
      await clearCode(userId);
      return res.status(200).json({
        success: true,
        message: '2FA verification successful',
        userId: userId,
      });
    } else {
      const attempts = await incrementAttemptCount(userId);
      const remaining = MAX_ATTEMPTS - attempts;

      if (remaining <= 0) {
        return res.status(429).json({
          success: false,
          message: 'Account locked due to too many failed attempts.',
          attemptsRemaining: 0,
        });
      }

      return res.status(401).json({
        success: false,
        message: 'Invalid verification code',
        attemptsRemaining: remaining,
      });
    }
  } catch (error) {
    console.error('Error in /api/2fa/verify:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
    });
  }
});

app.post('/api/2fa/resend', async (req, res) => {
  try {
    const { userId, phoneNumber } = req.body;

    if (!userId || !phoneNumber) {
      return res.status(400).json({
        success: false,
        message: 'userId and phoneNumber are required',
      });
    }

    const locked = await isUserLocked(userId);
    if (locked) {
      return res.status(429).json({
        success: false,
        message: 'Too many attempts. Please try again later.',
      });
    }

    const code = generateSixDigitCode();
    await storeCode(userId, code);

    try {
      await sendSMS(phoneNumber, code);
      return res.status(200).json({
        success: true,
        message: 'New SMS code sent successfully',
        expiresIn: CODE_EXPIRATION,
      });
    } catch (smsError) {
      return res.status(500).json({
        success: false,
        message: 'Failed to send SMS code',
      });
    }
  } catch (error) {
    console.error('Error in /api/2fa/resend:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
    });
  }
});

app.get('/api/2fa/status/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    if (!userId) {
      return res.status(400).json({
        success: false,
        message: 'userId is required',
      });
    }

    const attempts = await getAttemptCount(userId);
    const locked = attempts >= MAX_ATTEMPTS;
    const hasActiveSession = !!(await getStoredCode(userId));

    return res.status(200).json({
      success: true,
      userId: userId,
      locked: locked,
      attemptsRemaining: Math.max(0, MAX_ATTEMPTS - attempts),
      hasActiveSession: hasActiveSession,
    });
  } catch (error) {
    console.error('Error in /api/2fa/status:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
    });
  }
});

app.post('/api/2fa/reset/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    if (!userId) {
      return res.status(400).json({
        success: false,
        message: 'userId is required',
      });
    }

    await clearCode(userId);

    return res.status(200).json({
      success: true,
      message: '2FA session reset successfully',
    });
  } catch (error) {
    console.error('Error in /api/2fa/reset:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error',
    });
  }
});

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: '2FA SMS System' });
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`2FA SMS System running on port ${PORT}`);
});