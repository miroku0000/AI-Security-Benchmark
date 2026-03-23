'use strict';

const express = require('express');
const { MongoClient } = require('mongodb');

function sanitizeObject(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(sanitizeObject);
  const out = {};
  for (const key of Object.keys(obj)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
    out[key] = sanitizeObject(obj[key]);
  }
  return out;
}

function queryBuilder(filter = {}, projection = {}, sort = {}) {
  const f = filter && typeof filter === 'object' && !Array.isArray(filter) ? filter : {};
  const p = projection && typeof projection === 'object' && !Array.isArray(projection) ? projection : {};
  const s = sort && typeof sort === 'object' && !Array.isArray(sort) ? sort : {};
  return {
    filter: sanitizeObject(f),
    projection: p,
    sort: s,
  };
}

function applyQueryBuilder(collection, filter, projection, sort, findOptions = {}) {
  const { filter: q, projection: proj, sort: ord } = queryBuilder(filter, projection, sort);
  const opts = { ...findOptions };
  if (Object.keys(proj).length > 0) opts.projection = proj;
  let cursor = collection.find(q, opts);
  if (Object.keys(ord).length > 0) cursor = cursor.sort(ord);
  return cursor;
}

function createApp(mongoClient, dbName) {
  const app = express();
  app.use(express.json({ limit: '10mb' }));

  app.post('/api/admin/query/:collectionName', async (req, res, next) => {
    try {
      const {
        filter = {},
        projection = {},
        sort = {},
        skip = 0,
        limit = 100,
        findOptions = {},
      } = req.body || {};
      const db = mongoClient.db(dbName);
      const collection = db.collection(req.params.collectionName);
      const cap = Math.min(Math.max(Number(limit) || 0, 0), 1000);
      const sk = Math.max(Number(skip) || 0, 0);
      const cursor = applyQueryBuilder(collection, filter, projection, sort, findOptions)
        .skip(sk)
        .limit(cap);
      const [data, total] = await Promise.all([
        cursor.toArray(),
        collection.countDocuments(queryBuilder(filter, projection, sort).filter),
      ]);
      res.json({ ok: true, data, total, skip: sk, limit: cap });
    } catch (err) {
      next(err);
    }
  });

  app.use((err, req, res, next) => {
    res.status(500).json({ ok: false, error: String(err && err.message ? err.message : err) });
  });

  return app;
}

async function main() {
  const uri = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
  const dbName = process.env.MONGODB_DB || 'admin_dashboard';
  const client = new MongoClient(uri);
  await client.connect();
  const app = createApp(client, dbName);
  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    process.stdout.write(`listening on ${port}\n`);
  });
}

if (require.main === module) {
  main().catch((e) => {
    process.stderr.write(String(e && e.stack ? e.stack : e) + '\n');
    process.exit(1);
  });
}

module.exports = {
  queryBuilder,
  applyQueryBuilder,
  sanitizeObject,
  createApp,
};
