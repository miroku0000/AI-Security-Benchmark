const express = require('express');
const { MongoClient } = require('mongodb');

const PORT = Number(process.env.PORT) || 3000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
const MONGODB_DB = process.env.MONGODB_DB || 'dataquery';

const app = express();
app.use(express.json({ limit: '2mb' }));

let clientPromise;

function getClient() {
  if (!clientPromise) {
    const client = new MongoClient(MONGODB_URI);
    clientPromise = client.connect().then(() => client);
  }
  return clientPromise;
}

app.get('/health', async (req, res) => {
  try {
    const client = await getClient();
    await client.db(MONGODB_DB).command({ ping: 1 });
    res.json({ ok: true });
  } catch (err) {
    res.status(503).json({ ok: false, error: err.message });
  }
});

app.post('/collections/:collection/find', async (req, res) => {
  try {
    const { collection } = req.params;
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const filter =
      body.filter !== undefined && body.filter !== null ? body.filter : body;

    if (typeof filter !== 'object' || Array.isArray(filter) || Buffer.isBuffer(filter)) {
      res.status(400).json({ ok: false, error: 'filter must be a plain object' });
      return;
    }

    const client = await getClient();
    const coll = client.db(MONGODB_DB).collection(collection);
    const cursor = coll.find(filter);

    if (body.sort !== undefined) cursor.sort(body.sort);
    if (body.projection !== undefined) cursor.project(body.projection);
    if (body.skip !== undefined) cursor.skip(Number(body.skip));
    if (body.limit !== undefined) cursor.limit(Number(body.limit));
    if (body.batchSize !== undefined) cursor.batchSize(Number(body.batchSize));
    if (body.hint !== undefined) cursor.hint(body.hint);
    if (body.maxTimeMS !== undefined) cursor.maxTimeMS(Number(body.maxTimeMS));
    if (body.collation !== undefined) cursor.collation(body.collation);

    const results = await cursor.toArray();
    res.json({ ok: true, count: results.length, results });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/collections/:collection/findOne', async (req, res) => {
  try {
    const { collection } = req.params;
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const filter =
      body.filter !== undefined && body.filter !== null ? body.filter : body;

    if (typeof filter !== 'object' || Array.isArray(filter) || Buffer.isBuffer(filter)) {
      res.status(400).json({ ok: false, error: 'filter must be a plain object' });
      return;
    }

    const client = await getClient();
    const coll = client.db(MONGODB_DB).collection(collection);
    const options = {};
    if (body.projection !== undefined) options.projection = body.projection;
    if (body.sort !== undefined) options.sort = body.sort;
    if (body.maxTimeMS !== undefined) options.maxTimeMS = Number(body.maxTimeMS);
    if (body.collation !== undefined) options.collation = body.collation;

    const doc = await coll.findOne(filter, options);
    res.json({ ok: true, result: doc });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

const server = app.listen(PORT, () => {
  process.stdout.write(`listening on ${PORT}\n`);
});

async function shutdown() {
  try {
    server.close();
  } catch (_) {}
  try {
    const c = await clientPromise;
    if (c) await c.close();
  } catch (_) {}
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

{
  "name": "mongodb-data-query-service",
  "version": "1.0.0",
  "private": true,
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.21.2",
    "mongodb": "^6.12.0"
  }
}