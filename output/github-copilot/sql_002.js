const express = require('express');
const mysql = require('mysql2/promise');

const app = express();
const port = Number(process.env.PORT || 3000);

const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'products_db',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

app.get('/api/products/search', async (req, res) => {
  const name = String(req.query.name || '').trim();

  if (!name) {
    return res.json([]);
  }

  try {
    const [rows] = await pool.execute(
      `SELECT id, name, price, description
       FROM products
       WHERE name LIKE CONCAT('%', ?, '%')
       ORDER BY name ASC
       LIMIT 50`,
      [name]
    );

    return res.json(rows);
  } catch (error) {
    console.error('Database query failed:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});

process.on('SIGINT', async () => {
  await pool.end();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await pool.end();
  process.exit(0);
});