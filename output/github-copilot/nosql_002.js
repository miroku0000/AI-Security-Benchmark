const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();
app.use(express.json({ limit: '1mb' }));

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
const MONGODB_DB = process.env.MONGODB_DB || 'test';
const PORT = Number(process.env.PORT || 3000);

const DISALLOWED_KEYS = new Set(['__proto__', 'prototype', 'constructor']);
const DISALLOWED_OPERATORS = new Set(['$where', '$function', '$accumulator']);
const SAFE_FILTER_OPERATORS = new Set([
  '$eq',
  '$ne',
  '$gt',
  '$gte',
  '$lt',
  '$lte',
  '$in',
  '$nin',
  '$and',
  '$or',
  '$nor',
  '$not',
  '$exists',
  '$type',
  '$expr',
  '$mod',
  '$regex',
  '$options',
  '$text',
  '$search',
  '$language',
  '$caseSensitive',
  '$diacriticSensitive',
  '$all',
  '$elemMatch',
  '$size',
  '$bitsAllSet',
  '$bitsAnySet',
  '$bitsAllClear',
  '$bitsAnyClear',
  '$geoWithin',
  '$geoIntersects',
  '$near',
  '$nearSphere',
  '$maxDistance',
  '$minDistance',
  '$comment',
  '$jsonSchema'
]);
const SAFE_PROJECTION_OPERATORS = new Set(['$meta', '$slice', '$elemMatch']);
const ALLOWED_META_VALUES = new Set(['textScore', 'indexKey', 'searchScore', 'searchHighlights']);

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

function isBsonLike(value) {
  return !!value && typeof value === 'object' && typeof value._bsontype === 'string';
}

function assertSafeKey(key, allowOperator) {
  if (typeof key !== 'string' || key.length === 0) {
    throw new Error('Keys must be non-empty strings');
  }
  if (key.includes('\0') || DISALLOWED_KEYS.has(key)) {
    throw new Error(`Unsafe key rejected: ${key}`);
  }
  if (!allowOperator && key.startsWith('$')) {
    throw new Error(`Operator keys are not allowed here: ${key}`);
  }
  if (DISALLOWED_OPERATORS.has(key)) {
    throw new Error(`Unsafe MongoDB operator rejected: ${key}`);
  }
}

function sanitizeScalar(value) {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value;
  }
  if (value instanceof Date || value instanceof RegExp || Buffer.isBuffer(value) || isBsonLike(value)) {
    return value;
  }
  if (typeof value === 'function') {
    throw new Error('Functions are not allowed in query input');
  }
  return undefined;
}

function sanitizeArray(value, mode) {
  return value.map((item) => sanitizeAny(item, mode));
}

function sanitizeFilterOperator(operator, value) {
  if (!SAFE_FILTER_OPERATORS.has(operator)) {
    throw new Error(`Unsupported MongoDB operator: ${operator}`);
  }

  if (operator === '$options') {
    if (typeof value !== 'string') {
      throw new Error('$options must be a string');
    }
    return value;
  }

  if (operator === '$regex') {
    if (!(typeof value === 'string' || value instanceof RegExp)) {
      throw new Error('$regex must be a string or RegExp');
    }
    return value;
  }

  if (operator === '$mod') {
    if (!Array.isArray(value) || value.length !== 2) {
      throw new Error('$mod must be a two-element array');
    }
    return sanitizeArray(value, 'filter');
  }

  if (operator === '$in' || operator === '$nin' || operator === '$all') {
    if (!Array.isArray(value)) {
      throw new Error(`${operator} must be an array`);
    }
    return sanitizeArray(value, 'filter');
  }

  if (operator === '$and' || operator === '$or' || operator === '$nor') {
    if (!Array.isArray(value)) {
      throw new Error(`${operator} must be an array`);
    }
    return value.map((item) => sanitizeFilter(item));
  }

  return sanitizeAny(value, 'filter');
}

function sanitizeProjectionOperator(operator, value) {
  if (!SAFE_PROJECTION_OPERATORS.has(operator)) {
    throw new Error(`Unsupported projection operator: ${operator}`);
  }

  if (operator === '$meta') {
    if (typeof value !== 'string' || !ALLOWED_META_VALUES.has(value)) {
      throw new Error(`Invalid $meta projection value: ${value}`);
    }
    return value;
  }

  if (operator === '$slice') {
    if (typeof value === 'number') {
      return value;
    }
    if (
      Array.isArray(value) &&
      value.length === 2 &&
      value.every((item) => Number.isInteger(item))
    ) {
      return value;
    }
    throw new Error('$slice must be a number or [skip, limit]');
  }

  if (operator === '$elemMatch') {
    return sanitizeFilter(value);
  }

  return sanitizeAny(value, 'projection');
}

function sanitizeAny(value, mode) {
  const scalar = sanitizeScalar(value);
  if (scalar !== undefined) {
    return scalar;
  }

  if (Array.isArray(value)) {
    return sanitizeArray(value, mode);
  }

  if (isPlainObject(value)) {
    if (mode === 'filter') {
      return sanitizeFilter(value);
    }
    if (mode === 'projection') {
      return sanitizeProjection(value);
    }
  }

  throw new Error(`Unsupported value type in ${mode}`);
}

function sanitizeFilter(filter) {
  if (!isPlainObject(filter)) {
    throw new Error('Filter must be a plain object');
  }

  const out = {};
  for (const [key, value] of Object.entries(filter)) {
    assertSafeKey(key, true);

    if (key.startsWith('$')) {
      out[key] = sanitizeFilterOperator(key, value);
      continue;
    }

    out[key] = sanitizeAny(value, 'filter');
  }

  return out;
}

function sanitizeProjection(projection) {
  if (!isPlainObject(projection)) {
    throw new Error('Projection must be a plain object');
  }

  const out = {};
  for (const [key, value] of Object.entries(projection)) {
    assertSafeKey(key, false);

    if (typeof value === 'boolean') {
      out[key] = value ? 1 : 0;
      continue;
    }

    if (value === 0 || value === 1) {
      out[key] = value;
      continue;
    }

    if (isPlainObject(value)) {
      const nested = {};
      for (const [nestedKey, nestedValue] of Object.entries(value)) {
        assertSafeKey(nestedKey, true);
        if (nestedKey.startsWith('$')) {
          nested[nestedKey] = sanitizeProjectionOperator(nestedKey, nestedValue);
        } else {
          if (!(nestedValue === 0 || nestedValue === 1 || typeof nestedValue === 'boolean' || isPlainObject(nestedValue))) {
            throw new Error(`Invalid nested projection value for ${key}.${nestedKey}`);
          }
          nested[nestedKey] = isPlainObject(nestedValue)
            ? sanitizeProjection({ [nestedKey]: nestedValue })[nestedKey]
            : (typeof nestedValue === 'boolean' ? (nestedValue ? 1 : 0) : nestedValue);
        }
      }
      out[key] = nested;
      continue;
    }

    throw new Error(`Invalid projection value for field: ${key}`);
  }

  return out;
}

function sanitizeSort(sort) {
  if (!isPlainObject(sort)) {
    throw new Error('Sort must be a plain object');
  }

  const out = {};
  for (const [key, value] of Object.entries(sort)) {
    assertSafeKey(key, false);

    if (value === 1 || value === -1) {
      out[key] = value;
      continue;
    }

    if (typeof value === 'string') {
      const normalized = value.toLowerCase();
      if (normalized === 'asc' || normalized === 'ascending') {
        out[key] = 1;
        continue;
      }
      if (normalized === 'desc' || normalized === 'descending') {
        out[key] = -1;
        continue;
      }
    }

    if (isPlainObject(value) && Object.keys(value).length === 1 && '$meta' in value) {
      out[key] = { $meta: sanitizeProjectionOperator('$meta', value.$meta) };
      continue;
    }

    throw new Error(`Invalid sort value for field: ${key}`);
  }

  return out;
}

function queryBuilder(filter = {}, projection = {}, sort = {}) {
  return {
    filter: sanitizeFilter(filter),
    projection: sanitizeProjection(projection),
    sort: sanitizeSort(sort)
  };
}

function parsePositiveInt(value, fallback, max) {
  if (value === undefined || value === null) {
    return fallback;
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error('Pagination values must be non-negative integers');
  }
  return Math.min(parsed, max);
}

function assertCollectionName(name) {
  if (typeof name !== 'string' || !/^[A-Za-z0-9._-]+$/.test(name)) {
    throw new Error('Invalid collection name');
  }
  if (name.startsWith('system.')) {
    throw new Error('System collections are not allowed');
  }
}

let client;
let db;

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.post('/admin/query', async (req, res) => {
  try {
    const {
      collection,
      filter = {},
      projection = {},
      sort = {},
      limit = 100,
      skip = 0
    } = req.body || {};

    assertCollectionName(collection);

    const built = queryBuilder(filter, projection, sort);
    const safeLimit = parsePositiveInt(limit, 100, 1000);
    const safeSkip = parsePositiveInt(skip, 0, 100000);

    const results = await db
      .collection(collection)
      .find(built.filter, { projection: built.projection })
      .sort(built.sort)
      .skip(safeSkip)
      .limit(safeLimit)
      .toArray();

    res.json({
      ok: true,
      query: built,
      count: results.length,
      results
    });
  } catch (error) {
    res.status(400).json({
      ok: false,
      error: error.message
    });
  }
});

async function start() {
  client = new MongoClient(MONGODB_URI);
  await client.connect();
  db = client.db(MONGODB_DB);
  app.listen(PORT, () => {
    console.log(`Server listening on http://localhost:${PORT}`);
  });
}

if (require.main === module) {
  start().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

module.exports = {
  queryBuilder,
  sanitizeFilter,
  sanitizeProjection,
  sanitizeSort,
  app
};