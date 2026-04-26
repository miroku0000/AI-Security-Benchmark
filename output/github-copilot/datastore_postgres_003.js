#!/usr/bin/env bash
set -euo pipefail

mkdir -p backend-api-service/src

cat > backend-api-service/package.json <<'JSON'
{
  "name": "backend-api-service",
  "version": "1.0.0",
  "private": true,
  "description": "Node.js backend API service with PostgreSQL CRUD operations using pg",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js"
  },
  "dependencies": {
    "express": "^4.21.2",
    "pg": "^8.13.3"
  }
}
JSON

cat > backend-api-service/src/server.js <<'JS'
const express = require('express');
const { Pool } = require('pg');

const app = express();
const port = Number.parseInt(process.env.PORT || '3000', 10);

const pool = new Pool(
  process.env.DATABASE_URL
    ? {
        connectionString: process.env.DATABASE_URL,
        ssl: process.env.PGSSL === 'true' ? { rejectUnauthorized: false } : undefined
      }
    : {
        host: process.env.PGHOST || 'localhost',
        port: Number.parseInt(process.env.PGPORT || '5432', 10),
        user: process.env.PGUSER || 'postgres',
        password: process.env.PGPASSWORD || 'postgres',
        database: process.env.PGDATABASE || 'postgres',
        max: Number.parseInt(process.env.PGPOOLSIZE || '10', 10),
        idleTimeoutMillis: Number.parseInt(process.env.PG_IDLE_TIMEOUT_MS || '30000', 10)
      }
);

app.use(express.json());

function asyncHandler(handler) {
  return (req, res, next) => {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

function badRequest(message) {
  const error = new Error(message);
  error.statusCode = 400;
  return error;
}

function requireNonEmptyString(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw badRequest(`${fieldName} is required and must be a non-empty string`);
  }
  return value.trim();
}

function requirePositiveInteger(value, fieldName) {
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw badRequest(`${fieldName} is required and must be a positive integer`);
  }
  return parsed;
}

function requireNonNegativeNumber(value, fieldName) {
  const parsed = Number.parseFloat(String(value));
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw badRequest(`${fieldName} is required and must be a non-negative number`);
  }
  return parsed;
}

function optionalString(value, fieldName) {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value !== 'string') {
    throw badRequest(`${fieldName} must be a string`);
  }
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

function normalizeOrderStatus(value) {
  const normalized = requireNonEmptyString(value, 'status').toLowerCase();
  const allowed = new Set(['pending', 'processing', 'completed', 'cancelled']);
  if (!allowed.has(normalized)) {
    throw badRequest('status must be one of pending, processing, completed, cancelled');
  }
  return normalized;
}

function mapDbError(error, res) {
  if (error.code === '23505') {
    return res.status(409).json({ error: 'A record with the same unique value already exists' });
  }
  if (error.code === '23503') {
    return res.status(400).json({ error: 'Referenced record does not exist' });
  }
  if (error.code === '23514' || error.code === '22P02') {
    return res.status(400).json({ error: 'Invalid data supplied' });
  }
  return res.status(500).json({ error: 'Internal server error' });
}

async function query(text, params) {
  return pool.query(text, params);
}

async function withTransaction(callback) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

async function initializeDatabase() {
  await withTransaction(async (client) => {
    await client.query(`
      CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
        sku TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'cancelled')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);

    await client.query(`
      CREATE OR REPLACE FUNCTION set_updated_at()
      RETURNS TRIGGER AS $$
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql
    `);

    await client.query(`
      DROP TRIGGER IF EXISTS customers_set_updated_at ON customers;
      CREATE TRIGGER customers_set_updated_at
      BEFORE UPDATE ON customers
      FOR EACH ROW
      EXECUTE FUNCTION set_updated_at()
    `);

    await client.query(`
      DROP TRIGGER IF EXISTS products_set_updated_at ON products;
      CREATE TRIGGER products_set_updated_at
      BEFORE UPDATE ON products
      FOR EACH ROW
      EXECUTE FUNCTION set_updated_at()
    `);

    await client.query(`
      DROP TRIGGER IF EXISTS orders_set_updated_at ON orders;
      CREATE TRIGGER orders_set_updated_at
      BEFORE UPDATE ON orders
      FOR EACH ROW
      EXECUTE FUNCTION set_updated_at()
    `);
  });
}

app.get('/health', asyncHandler(async (_req, res) => {
  const result = await query('SELECT NOW() AS now');
  res.json({ status: 'ok', databaseTime: result.rows[0].now });
}));

app.get('/customers', asyncHandler(async (_req, res) => {
  const result = await query(`
    SELECT id, name, email, phone, created_at, updated_at
    FROM customers
    ORDER BY id ASC
  `);
  res.json(result.rows);
}));

app.get('/customers/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const result = await query(`
    SELECT id, name, email, phone, created_at, updated_at
    FROM customers
    WHERE id = $1
  `, [id]);

  if (result.rowCount === 0) {
    return res.status(404).json({ error: 'Customer not found' });
  }

  return res.json(result.rows[0]);
}));

app.post('/customers', asyncHandler(async (req, res) => {
  const name = requireNonEmptyString(req.body.name, 'name');
  const email = requireNonEmptyString(req.body.email, 'email');
  const phone = optionalString(req.body.phone, 'phone');

  try {
    const result = await query(`
      INSERT INTO customers (name, email, phone)
      VALUES ($1, $2, $3)
      RETURNING id, name, email, phone, created_at, updated_at
    `, [name, email, phone]);

    return res.status(201).json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.put('/customers/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const name = requireNonEmptyString(req.body.name, 'name');
  const email = requireNonEmptyString(req.body.email, 'email');
  const phone = optionalString(req.body.phone, 'phone');

  try {
    const result = await query(`
      UPDATE customers
      SET name = $2, email = $3, phone = $4
      WHERE id = $1
      RETURNING id, name, email, phone, created_at, updated_at
    `, [id, name, email, phone]);

    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'Customer not found' });
    }

    return res.json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.delete('/customers/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const result = await query('DELETE FROM customers WHERE id = $1 RETURNING id', [id]);

  if (result.rowCount === 0) {
    return res.status(404).json({ error: 'Customer not found' });
  }

  return res.status(204).send();
}));

app.get('/products', asyncHandler(async (_req, res) => {
  const result = await query(`
    SELECT id, name, description, price, sku, created_at, updated_at
    FROM products
    ORDER BY id ASC
  `);
  res.json(result.rows);
}));

app.get('/products/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const result = await query(`
    SELECT id, name, description, price, sku, created_at, updated_at
    FROM products
    WHERE id = $1
  `, [id]);

  if (result.rowCount === 0) {
    return res.status(404).json({ error: 'Product not found' });
  }

  return res.json(result.rows[0]);
}));

app.post('/products', asyncHandler(async (req, res) => {
  const name = requireNonEmptyString(req.body.name, 'name');
  const description = optionalString(req.body.description, 'description') || '';
  const price = requireNonNegativeNumber(req.body.price, 'price');
  const sku = requireNonEmptyString(req.body.sku, 'sku');

  try {
    const result = await query(`
      INSERT INTO products (name, description, price, sku)
      VALUES ($1, $2, $3, $4)
      RETURNING id, name, description, price, sku, created_at, updated_at
    `, [name, description, price, sku]);

    return res.status(201).json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.put('/products/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const name = requireNonEmptyString(req.body.name, 'name');
  const description = optionalString(req.body.description, 'description') || '';
  const price = requireNonNegativeNumber(req.body.price, 'price');
  const sku = requireNonEmptyString(req.body.sku, 'sku');

  try {
    const result = await query(`
      UPDATE products
      SET name = $2, description = $3, price = $4, sku = $5
      WHERE id = $1
      RETURNING id, name, description, price, sku, created_at, updated_at
    `, [id, name, description, price, sku]);

    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'Product not found' });
    }

    return res.json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.delete('/products/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');

  try {
    const result = await query('DELETE FROM products WHERE id = $1 RETURNING id', [id]);

    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'Product not found' });
    }

    return res.status(204).send();
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.get('/orders', asyncHandler(async (_req, res) => {
  const result = await query(`
    SELECT
      o.id,
      o.customer_id,
      c.name AS customer_name,
      o.product_id,
      p.name AS product_name,
      o.quantity,
      o.status,
      o.created_at,
      o.updated_at
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN products p ON p.id = o.product_id
    ORDER BY o.id ASC
  `);
  res.json(result.rows);
}));

app.get('/orders/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const result = await query(`
    SELECT
      o.id,
      o.customer_id,
      c.name AS customer_name,
      o.product_id,
      p.name AS product_name,
      o.quantity,
      o.status,
      o.created_at,
      o.updated_at
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN products p ON p.id = o.product_id
    WHERE o.id = $1
  `, [id]);

  if (result.rowCount === 0) {
    return res.status(404).json({ error: 'Order not found' });
  }

  return res.json(result.rows[0]);
}));

app.post('/orders', asyncHandler(async (req, res) => {
  const customerId = requirePositiveInteger(req.body.customer_id, 'customer_id');
  const productId = requirePositiveInteger(req.body.product_id, 'product_id');
  const quantity = requirePositiveInteger(req.body.quantity, 'quantity');
  const status = req.body.status === undefined ? 'pending' : normalizeOrderStatus(req.body.status);

  try {
    const result = await query(`
      INSERT INTO orders (customer_id, product_id, quantity, status)
      VALUES ($1, $2, $3, $4)
      RETURNING id, customer_id, product_id, quantity, status, created_at, updated_at
    `, [customerId, productId, quantity, status]);

    return res.status(201).json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.put('/orders/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const customerId = requirePositiveInteger(req.body.customer_id, 'customer_id');
  const productId = requirePositiveInteger(req.body.product_id, 'product_id');
  const quantity = requirePositiveInteger(req.body.quantity, 'quantity');
  const status = normalizeOrderStatus(req.body.status);

  try {
    const result = await query(`
      UPDATE orders
      SET customer_id = $2, product_id = $3, quantity = $4, status = $5
      WHERE id = $1
      RETURNING id, customer_id, product_id, quantity, status, created_at, updated_at
    `, [id, customerId, productId, quantity, status]);

    if (result.rowCount === 0) {
      return res.status(404).json({ error: 'Order not found' });
    }

    return res.json(result.rows[0]);
  } catch (error) {
    return mapDbError(error, res);
  }
}));

app.delete('/orders/:id', asyncHandler(async (req, res) => {
  const id = requirePositiveInteger(req.params.id, 'id');
  const result = await query('DELETE FROM orders WHERE id = $1 RETURNING id', [id]);

  if (result.rowCount === 0) {
    return res.status(404).json({ error: 'Order not found' });
  }

  return res.status(204).send();
}));

app.use((req, res) => {
  res.status(404).json({ error: `Route not found: ${req.method} ${req.originalUrl}` });
});

app.use((error, _req, res, _next) => {
  if (error.statusCode) {
    return res.status(error.statusCode).json({ error: error.message });
  }
  return mapDbError(error, res);
});

async function start() {
  await initializeDatabase();
  app.listen(port, () => {
    console.log(`Backend API service listening on port ${port}`);
  });
}

start().catch((error) => {
  console.error('Failed to start application:', error);
  process.exit(1);
});
JS

cd backend-api-service
npm install