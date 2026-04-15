const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();
app.use(express.json());

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017';
const DB_NAME = process.env.DB_NAME || 'dataquery';

let db;

MongoClient.connect(MONGO_URI).then(client => {
  db = client.db(DB_NAME);
  console.log('Connected to MongoDB');
});

const ALLOWED_OPERATORS = new Set([
  '$gt', '$gte', '$lt', '$lte', '$eq', '$ne',
  '$in', '$nin', '$exists', '$type',
  '$and', '$or', '$not', '$nor',
  '$regex', '$options',
  '$elemMatch', '$size', '$all'
]);

function sanitizeFilter(filter) {
  if (filter === null || typeof filter !== 'object') {
    return filter;
  }

  if (Array.isArray(filter)) {
    return filter.map(sanitizeFilter);
  }

  const sanitized = {};
  for (const [key, value] of Object.entries(filter)) {
    if (key.startsWith('$')) {
      if (!ALLOWED_OPERATORS.has(key)) {
        throw new Error(`Disallowed operator: ${key}`);
      }
      if (key === '$regex' && typeof value === 'string' && value.length > 200) {
        throw new Error('Regex pattern too long');
      }
    }

    if (key === '$where' || key === '$function' || key === '$accumulator') {
      throw new Error(`Disallowed operator: ${key}`);
    }

    sanitized[key] = sanitizeFilter(value);
  }
  return sanitized;
}

app.post('/api/:collection/query', async (req, res) => {
  try {
    const collectionName = req.params.collection.replace(/[^a-zA-Z0-9_]/g, '');
    const { filter = {}, projection, sort, limit = 100, skip = 0 } = req.body;

    const sanitizedFilter = sanitizeFilter(filter);
    const sanitizedProjection = projection ? sanitizeFilter(projection) : undefined;
    const sanitizedSort = sort ? sanitizeFilter(sort) : undefined;

    const cappedLimit = Math.min(Math.max(1, Number(limit) || 100), 1000);
    const cappedSkip = Math.max(0, Number(skip) || 0);

    let cursor = db.collection(collectionName).find(sanitizedFilter);

    if (sanitizedProjection) cursor = cursor.project(sanitizedProjection);
    if (sanitizedSort) cursor = cursor.sort(sanitizedSort);
    cursor = cursor.skip(cappedSkip).limit(cappedLimit);

    const results = await cursor.toArray();
    res.json({ count: results.length, data: results });
  } catch (err) {
    const status = err.message.startsWith('Disallowed') ? 400 : 500;
    res.status(status).json({ error: err.message });
  }
});

app.get('/api/:collection/count', async (req, res) => {
  try {
    const collectionName = req.params.collection.replace(/[^a-zA-Z0-9_]/g, '');
    const filter = req.query.filter ? sanitizeFilter(JSON.parse(req.query.filter)) : {};
    const count = await db.collection(collectionName).countDocuments(filter);
    res.json({ count });
  } catch (err) {
    const status = err.message.startsWith('Disallowed') ? 400 : 500;
    res.status(status).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Data query service running on port ${PORT}`));