'use strict';

const express = require('express');
const mysql = require('mysql2/promise');
require('dotenv').config();

const app = express();
const PORT = Number(process.env.PORT) || 3000;

const pool = mysql.createPool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT) || 3306,
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'app',
  waitForConnections: true,
  connectionLimit: Number(process.env.DB_POOL) || 10,
  queueLimit: 0,
});

app.get('/products/search', async (req, res) => {
  const q = req.query.q;
  if (typeof q !== 'string' || q.trim() === '') {
    res.status(400).json({ error: 'Query parameter q is required' });
    return;
  }
  const term = `%${q.trim()}%`;
  const limit = Math.min(Number(req.query.limit) || 50, 200);
  try {
    const [rows] = await pool.execute(
      'SELECT id, name, sku, price FROM products WHERE name LIKE ? ORDER BY name ASC LIMIT ?',
      [term, limit]
    );
    res.json({ products: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Search failed' });
  }
});

app.listen(PORT, () => {
  console.log('Listening on port', PORT);
});
