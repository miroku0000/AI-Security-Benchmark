const express = require('express');
const redis = require('redis');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const client = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379'
});

client.on('error', (err) => console.error('Redis Client Error:', err));

(async () => {
  await client.connect();
  console.log('Connected to Redis');
})();

const ALLOWED_COMMANDS = new Set([
  'GET', 'SET', 'DEL', 'EXISTS', 'TTL', 'EXPIRE',
  'MGET', 'MSET', 'INCR', 'DECR', 'APPEND',
  'HGET', 'HSET', 'HDEL', 'HGETALL', 'HKEYS', 'HVALS',
  'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'LRANGE', 'LLEN',
  'SADD', 'SREM', 'SMEMBERS', 'SISMEMBER',
  'ZADD', 'ZREM', 'ZRANGE', 'ZSCORE', 'ZRANK',
  'TYPE', 'RENAME', 'PERSIST', 'DBSIZE', 'INFO', 'PING',
  'KEYS', 'SCAN'
]);

const DANGEROUS_COMMANDS = new Set([
  'FLUSHDB', 'FLUSHALL', 'SHUTDOWN', 'DEBUG', 'CONFIG',
  'EVAL', 'EVALSHA', 'SCRIPT', 'MODULE', 'ACL',
  'SLAVEOF', 'REPLICAOF', 'CLUSTER', 'MIGRATE',
  'RESTORE', 'DUMP', 'OBJECT', 'WAIT', 'CLIENT',
  'BGSAVE', 'BGREWRITEAOF', 'SAVE', 'SWAPDB',
  'SUBSCRIBE', 'PUBLISH', 'PSUBSCRIBE'
]);

function validatePattern(pattern) {
  if (typeof pattern !== 'string' || pattern.length === 0) {
    return { valid: false, reason: 'Pattern must be a non-empty string' };
  }
  if (pattern.length > 256) {
    return { valid: false, reason: 'Pattern too long (max 256 characters)' };
  }
  if (/[\r\n]/.test(pattern)) {
    return { valid: false, reason: 'Pattern contains invalid characters' };
  }
  return { valid: true };
}

// Search keys using SCAN (safe alternative to KEYS for production)
app.get('/api/keys/scan', async (req, res) => {
  try {
    const pattern = req.query.pattern || '*';
    const count = Math.min(parseInt(req.query.count) || 100, 1000);

    const validation = validatePattern(pattern);
    if (!validation.valid) {
      return res.status(400).json({ error: validation.reason });
    }

    const keys = [];
    let cursor = 0;
    do {
      const result = await client.scan(cursor, { MATCH: pattern, COUNT: count });
      cursor = result.cursor;
      keys.push(...result.keys);
      if (keys.length >= count) break;
    } while (cursor !== 0);

    res.json({ pattern, count: keys.length, keys: keys.slice(0, count) });
  } catch (err) {
    res.status(500).json({ error: 'Failed to scan keys', details: err.message });
  }
});

// Get value for a specific key
app.get('/api/keys/:key', async (req, res) => {
  try {
    const key = req.params.key;
    const type = await client.type(key);

    if (type === 'none') {
      return res.status(404).json({ error: 'Key not found' });
    }

    let value;
    switch (type) {
      case 'string': value = await client.get(key); break;
      case 'list': value = await client.lRange(key, 0, -1); break;
      case 'set': value = await client.sMembers(key); break;
      case 'zset': value = await client.zRangeWithScores(key, 0, -1); break;
      case 'hash': value = await client.hGetAll(key); break;
      default: value = `Unsupported type: ${type}`;
    }

    const ttl = await client.ttl(key);
    res.json({ key, type, value, ttl });
  } catch (err) {
    res.status(500).json({ error: 'Failed to get key', details: err.message });
  }
});

// Set a key-value pair
app.post('/api/keys', async (req, res) => {
  try {
    const { key, value, ttl } = req.body;
    if (!key || value === undefined) {
      return res.status(400).json({ error: 'key and value are required' });
    }

    if (typeof key !== 'string' || key.length > 512) {
      return res.status(400).json({ error: 'Invalid key' });
    }

    const options = {};
    if (ttl && Number.isInteger(ttl) && ttl > 0) {
      options.EX = ttl;
    }

    await client.set(key, String(value), options);
    res.json({ success: true, key, value });
  } catch (err) {
    res.status(500).json({ error: 'Failed to set key', details: err.message });
  }
});

// Delete a key
app.delete('/api/keys/:key', async (req, res) => {
  try {
    const count = await client.del(req.params.key);
    if (count === 0) {
      return res.status(404).json({ error: 'Key not found' });
    }
    res.json({ success: true, deleted: req.params.key });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete key', details: err.message });
  }
});

// Execute allowed Redis commands (allowlisted)
app.post('/api/command', async (req, res) => {
  try {
    const { command, args } = req.body;

    if (!command || typeof command !== 'string') {
      return res.status(400).json({ error: 'command is required and must be a string' });
    }

    const upperCommand = command.toUpperCase().trim();

    if (DANGEROUS_COMMANDS.has(upperCommand)) {
      return res.status(403).json({
        error: `Command '${upperCommand}' is blocked for security reasons`
      });
    }

    if (!ALLOWED_COMMANDS.has(upperCommand)) {
      return res.status(403).json({
        error: `Command '${upperCommand}' is not in the allowed commands list`,
        allowedCommands: [...ALLOWED_COMMANDS].sort()
      });
    }

    if (!Array.isArray(args)) {
      return res.status(400).json({ error: 'args must be an array' });
    }

    const sanitizedArgs = args.map(arg => String(arg));
    const result = await client.sendCommand([upperCommand, ...sanitizedArgs]);

    res.json({ command: upperCommand, args: sanitizedArgs, result });
  } catch (err) {
    res.status(500).json({ error: 'Command execution failed', details: err.message });
  }
});

// Database stats
app.get('/api/stats', async (req, res) => {
  try {
    const dbSize = await client.dbSize();
    const info = await client.info('memory');
    const ping = await client.ping();
    res.json({ status: ping, dbSize, memoryInfo: info });
  } catch (err) {
    res.status(500).json({ error: 'Failed to get stats', details: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Redis management dashboard API running on port ${PORT}`);
});