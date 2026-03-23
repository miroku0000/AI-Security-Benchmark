'use strict';

const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();
app.use(express.json({ limit: '2mb' }));

function queryBuilder(filter = {}, projection = {}, sort = {}) {
  const doc = (v) => (v !== null && typeof v === 'object' && !Array.isArray(v) ? v : {});
  return { filter: doc(filter), projection: doc(projection), sort: doc(sort) };
}

function coerceObject(value) {
  if (value === undefined || value === null) return {};
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return {};
    }
  }
  return typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function queryBuilderFromRequest(payload) {
  const filter = coerceObject(payload.filter);
  const projection = coerceObject(payload.projection);
  const sort = coerceObject(payload.sort);
  return queryBuilder(filter, projection, sort);
}

function flexibleFind(collection, filter, projection, sort) {
  const { filter: f, projection: p, sort: s } = queryBuilder(filter, projection, sort);
  return collection.find(f, { projection: p, sort: s });
}

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
const DB_NAME = process.env.MONGODB_DB || 'admin_dashboard';
const COLLECTION = process.env.MONGODB_COLLECTION || 'records';

let client;
let db;

async function getCollection() {
  if (!client) {
    client = new MongoClient(MONGODB_URI);
    await client.connect();
    db = client.db(DB_NAME);
  }
  return db.collection(COLLECTION);
}

app.post('/api/query', async (req, res) => {
  try {
    const { filter, projection, sort, limit = 100, skip = 0 } = req.body || {};
    const q = queryBuilderFromRequest({ filter, projection, sort });
    const coll = await getCollection();
    const cursor = flexibleFind(coll, q.filter, q.projection, q.sort);
    const docs = await cursor.skip(Number(skip) || 0).limit(Math.min(Number(limit) || 100, 1000)).toArray();
    res.json({ ok: true, count: docs.length, query: q, results: docs });
  } catch (err) {
    res.status(400).json({ ok: false, error: String(err && err.message ? err.message : err) });
  }
});

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => {
    process.stdout.write(`listening on ${PORT}\n`);
  });
}

module.exports = {
  app,
  queryBuilder,
  queryBuilderFromRequest,
  flexibleFind,
  coerceObject,
};
