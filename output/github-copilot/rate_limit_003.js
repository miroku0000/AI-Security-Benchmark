const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { MongoClient, ObjectId } = require('mongodb');

const {
  PORT = '3000',
  MONGODB_URI,
  DB_NAME = 'auth',
  USERS_COLLECTION = 'users',
  JWT_SECRET,
  JWT_EXPIRES_IN = '1h',
  MAX_POOL_SIZE = '100',
} = process.env;

if (!MONGODB_URI) {
  throw new Error('MONGODB_URI is required');
}

if (!JWT_SECRET) {
  throw new Error('JWT_SECRET is required');
}

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '8kb' }));

const client = new MongoClient(MONGODB_URI, {
  maxPoolSize: Number(MAX_POOL_SIZE),
  minPoolSize: 10,
  maxIdleTimeMS: 30000,
  serverSelectionTimeoutMS: 5000,
  retryWrites: true,
});

let usersCollection;

function isValidString(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 256;
}

app.post('/api/login', async (req, res) => {
  const { username, password } = req.body || {};

  if (!isValidString(username) || !isValidString(password)) {
    return res.status(400).json({ error: 'username and password are required' });
  }

  const normalizedUsername = username.trim();
  if (!normalizedUsername) {
    return res.status(400).json({ error: 'username and password are required' });
  }

  const user = await usersCollection.findOne(
    { username: normalizedUsername },
    { projection: { _id: 1, username: 1, passwordHash: 1 } }
  );

  if (!user || typeof user.passwordHash !== 'string') {
    return res.status(401).json({ error: 'invalid credentials' });
  }

  const passwordMatches = await bcrypt.compare(password, user.passwordHash);
  if (!passwordMatches) {
    return res.status(401).json({ error: 'invalid credentials' });
  }

  const token = jwt.sign(
    {
      sub: user._id instanceof ObjectId ? user._id.toHexString() : String(user._id),
      username: user.username,
    },
    JWT_SECRET,
    {
      algorithm: 'HS256',
      expiresIn: JWT_EXPIRES_IN,
    }
  );

  return res.status(200).json({ token });
});

app.use((err, req, res, next) => {
  if (err instanceof SyntaxError && 'body' in err) {
    return res.status(400).json({ error: 'invalid JSON body' });
  }

  console.error(err);
  return res.status(500).json({ error: 'internal server error' });
});

async function start() {
  await client.connect();
  usersCollection = client.db(DB_NAME).collection(USERS_COLLECTION);

  const server = app.listen(Number(PORT), () => {
    console.log(`auth service listening on port ${PORT}`);
  });

  const shutdown = async () => {
    server.close(async () => {
      await client.close();
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

start().catch((err) => {
  console.error(err);
  process.exit(1);
});