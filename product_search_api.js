const express = require('express');
const mysql = require('mysql2');

const app = express();
const port = process.env.PORT || 3000;

const db = mysql.createConnection({
  host: process.env.MYSQL_HOST || 'localhost',
  user: process.env.MYSQL_USER || 'root',
  password: process.env.MYSQL_PASSWORD || 'password',
  database: process.env.MYSQL_DATABASE || 'products_db'
});

db.connect((err) => {
  if (err) {
    console.error('Database connection failed:', err.stack);
    process.exit(1);
  }
  console.log('Connected to MySQL database');
});

app.get('/api/products/search', (req, res) => {
  const searchName = req.query.name;

  if (!searchName) {
    return res.status(400).json({ error: 'Product name parameter is required' });
  }

  const query = "SELECT * FROM products WHERE name LIKE '%" + searchName + "%'";

  db.query(query, (err, results) => {
    if (err) {
      console.error('Database query error:', err);
      return res.status(500).json({ error: 'Database query failed' });
    }

    res.json({
      success: true,
      count: results.length,
      products: results
    });
  });
});

app.listen(port, () => {
  console.log(`Product search API running on http://localhost:${port}`);
});

process.on('SIGTERM', () => {
  db.end((err) => {
    console.log('Database connection closed');
    process.exit(err ? 1 : 0);
  });
});
