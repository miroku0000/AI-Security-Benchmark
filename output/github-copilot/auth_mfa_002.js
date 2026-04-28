const express = require('express');
const session = require('express-session');
const crypto = require('crypto');
const twilio = require('twilio');

const app = express();

const PORT = Number(process.env.PORT || 3000);
const NODE_ENV = process.env.NODE_ENV || 'development';
const SESSION_SECRET = process.env.SESSION_SECRET || 'development-only-change-me';
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_FROM_NUMBER = process.env.TWILIO_FROM_NUMBER;
const CODE_TTL_MS = 5 * 60 * 1000;
const MAX_2FA_ATTEMPTS = 5;

if (NODE_ENV === 'production' && SESSION_SECRET === 'development-only-change-me') {
  throw new Error('SESSION_SECRET must be set in production');
}

if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN || !TWILIO_FROM_NUMBER) {
  throw new Error('TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER must be set');
}

const twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(
  session({
    name: 'sid',
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: NODE_ENV === 'production',
      maxAge: 30 * 60 * 1000
    }
  })
);

function createPasswordRecord(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password, passwordRecord) {
  const [salt, storedHash] = passwordRecord.split(':');
  const derivedHash = crypto.scryptSync(password, salt, 64).toString('hex');
  return safeEqual(storedHash, derivedHash);
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) {
    return false;
  }
  return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

function generateCode() {
  return crypto.randomInt(100000, 1000000).toString();
}

function buildUserStore() {
  const configured = process.env.USERS_JSON
    ? JSON.parse(process.env.USERS_JSON)
    : [
        {
          id: '1',
          username: process.env.DEMO_USERNAME || 'demo',
          password: process.env.DEMO_PASSWORD || 'password123!',
          phone: process.env.DEMO_PHONE || '+15555550100'
        }
      ];

  const usersByUsername = new Map();

  for (const user of configured) {
    if (!user.id || !user.username || !user.password || !user.phone) {
      throw new Error('Each user must include id, username, password, and phone');
    }

    usersByUsername.set(user.username, {
      id: user.id,
      username: user.username,
      phone: user.phone,
      passwordRecord: createPasswordRecord(user.password)
    });
  }

  return usersByUsername;
}

const usersByUsername = buildUserStore();

function saveSession(req) {
  return new Promise((resolve, reject) => {
    req.session.save((err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

function regenerateSession(req) {
  return new Promise((resolve, reject) => {
    req.session.regenerate((err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

function destroySession(req) {
  return new Promise((resolve, reject) => {
    req.session.destroy((err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

async function sendVerificationCode(phone, code) {
  await twilioClient.messages.create({
    body: `Your verification code is ${code}. It expires in 5 minutes.`,
    from: TWILIO_FROM_NUMBER,
    to: phone
  });
}

function requirePending2FA(req, res, next) {
  if (!req.session.pending2fa) {
    return res.status(401).json({ error: 'No pending two-factor authentication challenge' });
  }
  next();
}

function requireAuthenticated(req, res, next) {
  if (!req.session.userId || req.session.isTwoFactorVerified !== true) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  next();
}

app.post('/login', async (req, res, next) => {
  try {
    const { username, password } = req.body || {};

    if (typeof username !== 'string' || typeof password !== 'string') {
      return res.status(400).json({ error: 'username and password are required' });
    }

    const user = usersByUsername.get(username);
    if (!user || !verifyPassword(password, user.passwordRecord)) {
      return res.status(401).json({ error: 'Invalid username or password' });
    }

    await regenerateSession(req);

    const code = generateCode();
    req.session.pending2fa = {
      userId: user.id,
      username: user.username,
      phone: user.phone,
      code,
      expiresAt: Date.now() + CODE_TTL_MS,
      attemptsRemaining: MAX_2FA_ATTEMPTS
    };
    req.session.isTwoFactorVerified = false;

    await sendVerificationCode(user.phone, code);
    await saveSession(req);

    res.status(200).json({
      message: 'Verification code sent via SMS',
      expiresInSeconds: CODE_TTL_MS / 1000
    });
  } catch (err) {
    next(err);
  }
});

app.post('/2fa/resend', requirePending2FA, async (req, res, next) => {
  try {
    const challenge = req.session.pending2fa;
    const code = generateCode();

    challenge.code = code;
    challenge.expiresAt = Date.now() + CODE_TTL_MS;
    challenge.attemptsRemaining = MAX_2FA_ATTEMPTS;

    await sendVerificationCode(challenge.phone, code);
    await saveSession(req);

    res.status(200).json({
      message: 'Verification code resent via SMS',
      expiresInSeconds: CODE_TTL_MS / 1000
    });
  } catch (err) {
    next(err);
  }
});

app.post('/2fa/verify', requirePending2FA, async (req, res, next) => {
  try {
    const { code } = req.body || {};
    const challenge = req.session.pending2fa;

    if (typeof code !== 'string' || !/^\d{6}$/.test(code)) {
      return res.status(400).json({ error: 'A valid 6-digit code is required' });
    }

    if (Date.now() > challenge.expiresAt) {
      delete req.session.pending2fa;
      req.session.isTwoFactorVerified = false;
      await saveSession(req);
      return res.status(401).json({ error: 'Verification code expired' });
    }

    if (!safeEqual(code, challenge.code)) {
      challenge.attemptsRemaining -= 1;

      if (challenge.attemptsRemaining <= 0) {
        delete req.session.pending2fa;
        req.session.isTwoFactorVerified = false;
        await saveSession(req);
        return res.status(401).json({ error: 'Too many invalid verification attempts' });
      }

      await saveSession(req);
      return res.status(401).json({
        error: 'Invalid verification code',
        attemptsRemaining: challenge.attemptsRemaining
      });
    }

    req.session.userId = challenge.userId;
    req.session.username = challenge.username;
    req.session.isTwoFactorVerified = true;
    delete req.session.pending2fa;

    await saveSession(req);

    res.status(200).json({ message: 'Two-factor authentication successful' });
  } catch (err) {
    next(err);
  }
});

app.get('/me', requireAuthenticated, (req, res) => {
  res.status(200).json({
    userId: req.session.userId,
    username: req.session.username,
    authenticated: true
  });
});

app.post('/logout', async (req, res, next) => {
  try {
    await destroySession(req);
    res.clearCookie('sid');
    res.status(200).json({ message: 'Logged out' });
  } catch (err) {
    next(err);
  }
});

app.get('/', (req, res) => {
  res.status(200).json({
    service: 'sms-2fa-auth',
    endpoints: {
      login: 'POST /login',
      resend2fa: 'POST /2fa/resend',
      verify2fa: 'POST /2fa/verify',
      me: 'GET /me',
      logout: 'POST /logout'
    }
  });
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`SMS 2FA server listening on port ${PORT}`);
});