const express = require("express");
const mysql = require("mysql2/promise");

const app = express();
const port = Number(process.env.PORT) || 3000;

const pool = mysql.createPool({
  host: process.env.DB_HOST || "localhost",
  user: process.env.DB_USER || "your_user",
  password: process.env.DB_PASSWORD || "your_password",
  database: process.env.DB_NAME || "your_database",
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

app.get("/products/search", async (req, res) => {
  const q = (req.query.q || "").trim();
  if (!q) {
    return res.status(400).json({ error: "Missing search term" });
  }

  try {
    const [rows] = await pool.query(
      "SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY name ASC LIMIT 50",
      [`%${q}%`]
    );
    return res.json({ count: rows.length, results: rows });
  } catch (error) {
    return res.status(500).json({ error: "Database query failed" });
  }
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});