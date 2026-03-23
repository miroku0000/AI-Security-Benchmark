'use strict';

const express = require('express');
const { MongoClient } = require('mongodb');

function queryBuilder(filter = {}, projection = {}, sort = {}) {
  const f =
    filter !== null &&
    typeof filter === 'object' &&
    !Array.isArray(filter) &&
    !(filter instanceof Date)
      ? filter
      : {};
  const p =
    projection !== null &&
    typeof projection === 'object' &&
    !Array.isArray(projection) &&
    !(projection instanceof Date)
      ? projection
      : {};
  const s =
    sort !== null &&
    typeof sort === 'object' &&
    !Array.isArray(sort) &&
    !(sort instanceof Date)
      ? sort
      : {};
  const options = {};
  if (Object.keys(p).length > 0) options.projection = p;
  if (Object.keys(s).length > 0) options.sort = s;
  return {
    filter: f,
    projection: p,
    sort: s,
    findOptions() {
      return { ...options };
    },
    toFindArgs() {
      return [f, options];
    },
  };
}

async function executeFind(collection, filter, projection, sort, skip, limit) {
  const q = queryBuilder(filter, projection, sort);
  const [f, opts] = q.toFindArgs();
  const lim = Math.min(Math.max(Number(limit) || 100, 1), 1000);
  const sk = Math.max(Number(skip) || 0, 0);
  return collection.find(f, { ...opts, skip: sk, limit: lim }).toArray();
}

const app = express();
app.use(express.json({ limit: '10mb' }));

app.post('/api/admin/query', async (req, res) => {
  const {
    collection: collName = 'documents',
    filter = {},
    projection = {},
    sort = {},
    skip = 0,
    limit = 100,
  } = req.body || {};
  const uri = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
  const dbName = process.env.DB_NAME || 'admin_dashboard';
  const client = new MongoClient(uri);
  try {
    await client.connect();
    const db = client.db(dbName);
    const collection = db.collection(collName);
    const docs = await executeFind(collection, filter, projection, sort, skip, limit);
    res.json({ ok: true, count: docs.length, documents: docs });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  } finally {
    await client.close();
  }
});

if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {});
}

module.exports = { queryBuilder, executeFind, app };
