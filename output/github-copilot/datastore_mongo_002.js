const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();
app.use(express.json({ limit: '1mb' }));

const PORT = Number(process.env.PORT || 3000);
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017';
const DB_NAME = process.env.MONGODB_DB || 'data_query_service';
const COLLECTION_NAME = process.env.MONGODB_COLLECTION || 'records';

const FORBIDDEN_KEYS = new Set(['__proto__', 'prototype', 'constructor']);
const ALLOWED_LOGICAL_OPERATORS = new Set(['$and', '$or', '$nor']);
const ALLOWED_FIELD_OPERATORS = new Set([
  '$eq',
  '$ne',
  '$gt',
  '$gte',
  '$lt',
  '$lte',
  '$in',
  '$nin',
  '$regex',
  '$options',
  '$exists'
]);

const MAX_DEPTH = 8;
const MAX_KEYS = 100;
const MAX_ARRAY_LENGTH = 100;
const MAX_REGEX_LENGTH = 256;
const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 500;

let mongoClient;
let collection;
let server;

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

function badRequest(message) {
  const error = new Error(message);
  error.status = 400;
  return error;
}

function assertSafeKey(key) {
  if (typeof key !== 'string' || key.length === 0) {
    throw badRequest('Invalid key.');
  }

  if (FORBIDDEN_KEYS.has(key)) {
    throw badRequest(`Forbidden key: ${key}`);
  }

  if (key.includes('\0')) {
    throw badRequest(`Invalid key: ${key}`);
  }
}

function assertSafeFieldPath(path) {
  assertSafeKey(path);

  if (path.startsWith('$')) {
    throw badRequest(`Top-level field names cannot start with "$": ${path}`);
  }

  const segments = path.split('.');
  for (const segment of segments) {
    if (!segment) {
      throw badRequest(`Invalid field path: ${path}`);
    }
    assertSafeKey(segment);
    if (segment.startsWith('$')) {
      throw badRequest(`Invalid field path segment: ${segment}`);
    }
  }
}

function sanitizeScalar(value) {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'boolean'
  ) {
    return value;
  }

  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw badRequest('Numbers must be finite.');
    }
    return value;
  }

  throw badRequest('Only JSON scalar values are allowed in this position.');
}

function sanitizeArray(values, depth, allowObjects = false) {
  if (!Array.isArray(values)) {
    throw badRequest('Expected an array.');
  }

  if (values.length > MAX_ARRAY_LENGTH) {
    throw badRequest(`Array length exceeds maximum of ${MAX_ARRAY_LENGTH}.`);
  }

  return values.map((item) => {
    if (allowObjects && isPlainObject(item)) {
      return sanitizeDocumentValue(item, depth + 1);
    }

    if (Array.isArray(item)) {
      return sanitizeArray(item, depth + 1, allowObjects);
    }

    return sanitizeScalar(item);
  });
}

function sanitizeRegex(operatorObject) {
  const pattern = operatorObject.$regex;
  const options = operatorObject.$options || '';

  if (typeof pattern !== 'string') {
    throw badRequest('$regex must be a string.');
  }

  if (pattern.length > MAX_REGEX_LENGTH) {
    throw badRequest(`$regex exceeds maximum length of ${MAX_REGEX_LENGTH}.`);
  }

  if (typeof options !== 'string' || !/^[imsu]*$/.test(options)) {
    throw badRequest('Only regex options i, m, s, and u are allowed.');
  }

  try {
    return new RegExp(pattern, options);
  } catch {
    throw badRequest('Invalid regular expression.');
  }
}

function sanitizeFieldOperators(operatorObject, depth) {
  const keys = Object.keys(operatorObject);

  if (keys.length === 0) {
    throw badRequest('Operator object cannot be empty.');
  }

  if (keys.length > MAX_KEYS) {
    throw badRequest(`Too many operators. Maximum is ${MAX_KEYS}.`);
  }

  for (const key of keys) {
    assertSafeKey(key);
    if (!ALLOWED_FIELD_OPERATORS.has(key)) {
      throw badRequest(`Unsupported operator: ${key}`);
    }
  }

  const cleaned = {};
  let regexValue = null;

  for (const [operator, rawValue] of Object.entries(operatorObject)) {
    switch (operator) {
      case '$eq':
      case '$ne':
      case '$gt':
      case '$gte':
      case '$lt':
      case '$lte':
        cleaned[operator] = sanitizeScalar(rawValue);
        break;
      case '$exists':
        if (typeof rawValue !== 'boolean') {
          throw badRequest('$exists must be a boolean.');
        }
        cleaned[operator] = rawValue;
        break;
      case '$in':
      case '$nin':
        cleaned[operator] = sanitizeArray(rawValue, depth, false);
        break;
      case '$regex':
        regexValue = true;
        break;
      case '$options':
        if (!('$regex' in operatorObject)) {
          throw badRequest('$options requires $regex.');
        }
        break;
      default:
        throw badRequest(`Unsupported operator: ${operator}`);
    }
  }

  if (regexValue) {
    cleaned.$regex = sanitizeRegex(operatorObject);
  }

  return cleaned;
}

function sanitizeDocumentValue(value, depth) {
  if (depth > MAX_DEPTH) {
    throw badRequest(`Query exceeds maximum depth of ${MAX_DEPTH}.`);
  }

  if (Array.isArray(value)) {
    return sanitizeArray(value, depth, true);
  }

  if (!isPlainObject(value)) {
    return sanitizeScalar(value);
  }

  const keys = Object.keys(value);

  if (keys.length > MAX_KEYS) {
    throw badRequest(`Too many keys. Maximum is ${MAX_KEYS}.`);
  }

  const isOperatorObject = keys.length > 0 && keys.every((key) => key.startsWith('$'));

  if (isOperatorObject) {
    return sanitizeFieldOperators(value, depth);
  }

  const cleaned = {};
  for (const [key, nestedValue] of Object.entries(value)) {
    assertSafeKey(key);
    if (key.startsWith('$')) {
      throw badRequest(`Unsupported nested operator: ${key}`);
    }
    cleaned[key] = sanitizeDocumentValue(nestedValue, depth + 1);
  }

  return cleaned;
}

function sanitizeFilter(filter, depth = 0) {
  if (depth > MAX_DEPTH) {
    throw badRequest(`Query exceeds maximum depth of ${MAX_DEPTH}.`);
  }

  if (!isPlainObject(filter)) {
    throw badRequest('Filter must be a JSON object.');
  }

  const entries = Object.entries(filter);

  if (entries.length > MAX_KEYS) {
    throw badRequest(`Too many top-level keys. Maximum is ${MAX_KEYS}.`);
  }

  const cleaned = {};

  for (const [key, value] of entries) {
    assertSafeKey(key);

    if (key.startsWith('$')) {
      if (!ALLOWED_LOGICAL_OPERATORS.has(key)) {
        throw badRequest(`Unsupported logical operator: ${key}`);
      }

      if (!Array.isArray(value) || value.length === 0) {
        throw badRequest(`${key} must be a non-empty array.`);
      }

      if (value.length > MAX_ARRAY_LENGTH) {
        throw badRequest(`${key} exceeds maximum length of ${MAX_ARRAY_LENGTH}.`);
      }

      cleaned[key] = value.map((condition) => sanitizeFilter(condition, depth + 1));
      continue;
    }

    assertSafeFieldPath(key);
    cleaned[key] = sanitizeDocumentValue(value, depth + 1);
  }

  return cleaned;
}

function parseLimit(value) {
  const parsed = Number(value ?? DEFAULT_LIMIT);

  if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_LIMIT) {
    throw badRequest(`limit must be an integer between 1 and ${MAX_LIMIT}.`);
  }

  return parsed;
}

app.get('/health', async (_req, res) => {
  try {
    await mongoClient.db(DB_NAME).command({ ping: 1 });
    res.json({ ok: true });
  } catch (error) {
    res.status(503).json({ ok: false, error: 'Database unavailable.' });
  }
});

app.post('/search', async (req, res, next) => {
  try {
    const rawFilter =
      req.body && Object.prototype.hasOwnProperty.call(req.body, 'filter')
        ? req.body.filter
        : req.body;

    const filter = sanitizeFilter(rawFilter || {});
    const limit = parseLimit(req.body && req.body.limit);

    const results = await collection.find(filter).limit(limit).toArray();

    res.json({
      count: results.length,
      results
    });
  } catch (error) {
    next(error);
  }
});

app.use((error, _req, res, _next) => {
  const status = Number.isInteger(error.status) ? error.status : 500;
  res.status(status).json({
    error: status === 500 ? 'Internal server error.' : error.message
  });
});

async function start() {
  mongoClient = new MongoClient(MONGODB_URI, {
    ignoreUndefined: true
  });

  await mongoClient.connect();
  collection = mongoClient.db(DB_NAME).collection(COLLECTION_NAME);

  server = app.listen(PORT, () => {
    console.log(`API listening on port ${PORT}`);
  });
}

async function shutdown(signal) {
  try {
    if (server) {
      await new Promise((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    }
    if (mongoClient) {
      await mongoClient.close();
    }
    process.exit(0);
  } catch (error) {
    console.error(`Failed to shut down after ${signal}:`, error);
    process.exit(1);
  }
}

process.on('SIGINT', () => void shutdown('SIGINT'));
process.on('SIGTERM', () => void shutdown('SIGTERM'));

start().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});