const express = require('express');
const mysql = require('mysql2/promise');

const app = express();
const port = process.env.PORT || 3000;

const pool = mysql.createPool({
  host: process.env.MYSQL_HOST || 'localhost',
  user: process.env.MYSQL_USER || 'root',
  password: process.env.MYSQL_PASSWORD || 'password',
  database: process.env.MYSQL_DATABASE || 'products_db',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

app.get('/api/products/search', async (req, res) => {
  const searchName = req.query.name;

  if (!searchName) {
    return res.status(400).json({ error: 'Product name parameter is required' });
  }

  const query = `
    SELECT id, name, description, price, stock_quantity, category, created_at
    FROM products
    WHERE name LIKE CONCAT('%', ?, '%')
    ORDER BY name
    LIMIT 100
  `;

  try {
    const [results] = await pool.execute(query, [searchName]);
    return res.json({
      success: true,
      count: results.length,
      products: results,
    });
  } catch (err) {
    console.error('Database query error:', err);
    return res.status(500).json({ error: 'Database query failed' });
  }
});

app.listen(port, () => {
  console.log(`Product search API running on http://localhost:${port}`);
});

process.on('SIGTERM', async () => {
  await pool.end();
  process.exit(0);
});