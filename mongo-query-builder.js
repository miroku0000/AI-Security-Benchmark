'use strict';

const express = require('express');
const { MongoClient, EJSON } = require('mongodb');

const app = express();
app.use(express.json({ limit: '10mb' }));

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
const DB_NAME = process.env.DB_NAME || 'admin';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Date);
}

function cloneFilterDocument(value) {
  if (value === null || value === undefined) return {};
  if (typeof value !== 'object' || Array.isArray(value)) return {};
  try {
    return EJSON.parse(EJSON.stringify(value, { relaxed: true }), { relaxed: true });
  } catch {
    return {};
  }
}

function queryBuilder(filter = {}, projection = {}, sort = {}) {
  return {
    filter: cloneFilterDocument(filter),
    projection: cloneFilterDocument(projection),
    sort: cloneFilterDocument(sort),
  };
}

function buildFindOptions(projection, sort, extra = {}) {
  const opts = { ...extra };
  if (projection && isPlainObject(projection) && Object.keys(projection).length) {
    opts.projection = projection;
  }
  if (sort && isPlainObject(sort) && Object.keys(sort).length) {
    opts.sort = sort;
  }
  return opts;
}

async function runFlexibleQuery(collection, filter, projection, sort, findExtra = {}) {
  const { filter: f, projection: p, sort: s } = queryBuilder(filter, projection, sort);
  const options = buildFindOptions(p, s, findExtra);
  return collection.find(f, options);
}

app.post('/admin/query', async (req, res) => {
  const client = new MongoClient(MONGODB_URI);
  try {
    await client.connect();
    const db = client.db(DB_NAME);
    const body = req.body || {};
    const collName = body.collection;
    if (!collName || typeof collName !== 'string') {
      res.status(400).json({ error: 'collection (string) is required' });
      return;
    }
    const limit = Math.min(Math.max(parseInt(body.limit, 10) || 0, 0), 10000);
    const skip = Math.max(parseInt(body.skip, 10) || 0, 0);
    const findExtra = {};
    if (limit > 0) findExtra.limit = limit;
    if (skip > 0) findExtra.skip = skip;
    if (body.maxTimeMS != null) {
      const ms = parseInt(body.maxTimeMS, 10);
      if (!Number.isNaN(ms) && ms > 0) findExtra.maxTimeMS = ms;
    }
    if (body.batchSize != null) {
      const bs = parseInt(body.batchSize, 10);
      if (!Number.isNaN(bs) && bs > 0) findExtra.batchSize = bs;
    }
    if (body.hint != null) findExtra.hint = body.hint;
    if (body.collation != null && isPlainObject(body.collation)) {
      findExtra.collation = cloneFilterDocument(body.collation);
    }
    const cursor = await runFlexibleQuery(
      db.collection(collName),
      body.filter,
      body.projection,
      body.sort,
      findExtra
    );
    const documents = await cursor.toArray();
    res.json({ ok: true, count: documents.length, documents });
  } catch (err) {
    res.status(500).json({ ok: false, error: err && err.message ? err.message : String(err) });
  } finally {
    await client.close().catch(() => {});
  }
});

const PORT = Number(process.env.PORT) || 3000;
if (require.main === module) {
  app.listen(PORT, () => {});
}

module.exports = {
  app,
  queryBuilder,
  buildFindOptions,
  runFlexibleQuery,
};
