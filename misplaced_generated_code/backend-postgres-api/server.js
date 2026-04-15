require("dotenv").config();
const express = require("express");
const { Pool } = require("pg");

const app = express();
app.use(express.json());

const pool = new Pool({
  host: process.env.PGHOST || "localhost",
  port: Number(process.env.PGPORT || 5432),
  user: process.env.PGUSER || "postgres",
  password: process.env.PGPASSWORD || "",
  database: process.env.PGDATABASE || "postgres",
});

function asyncHandler(fn) {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

app.get("/health", asyncHandler(async (_req, res) => {
  await pool.query("SELECT 1");
  res.json({ ok: true });
}));

app.get("/api/users", asyncHandler(async (_req, res) => {
  const { rows } = await pool.query(
    "SELECT id, name, email, created_at FROM users ORDER BY id"
  );
  res.json(rows);
}));

app.get("/api/users/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rows } = await pool.query(
    "SELECT id, name, email, created_at FROM users WHERE id = $1",
    [id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.post("/api/users", asyncHandler(async (req, res) => {
  const { name, email } = req.body || {};
  if (!name || !email) {
    return res.status(400).json({ error: "name and email required" });
  }
  const { rows } = await pool.query(
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, name, email, created_at",
    [name, email]
  );
  res.status(201).json(rows[0]);
}));

app.put("/api/users/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { name, email } = req.body || {};
  const { rows } = await pool.query(
    `UPDATE users SET
       name = COALESCE($1, name),
       email = COALESCE($2, email)
     WHERE id = $3
     RETURNING id, name, email, created_at`,
    [name ?? null, email ?? null, id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.delete("/api/users/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rowCount } = await pool.query("DELETE FROM users WHERE id = $1", [id]);
  if (!rowCount) return res.status(404).json({ error: "Not found" });
  res.status(204).send();
}));

app.get("/api/products", asyncHandler(async (_req, res) => {
  const { rows } = await pool.query(
    "SELECT id, name, price, stock, created_at FROM products ORDER BY id"
  );
  res.json(rows);
}));

app.get("/api/products/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rows } = await pool.query(
    "SELECT id, name, price, stock, created_at FROM products WHERE id = $1",
    [id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.post("/api/products", asyncHandler(async (req, res) => {
  const { name, price, stock } = req.body || {};
  if (!name) return res.status(400).json({ error: "name required" });
  const { rows } = await pool.query(
    `INSERT INTO products (name, price, stock)
     VALUES ($1, $2, $3)
     RETURNING id, name, price, stock, created_at`,
    [name, price ?? 0, stock ?? 0]
  );
  res.status(201).json(rows[0]);
}));

app.put("/api/products/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { name, price, stock } = req.body || {};
  const { rows } = await pool.query(
    `UPDATE products SET
       name = COALESCE($1, name),
       price = COALESCE($2, price),
       stock = COALESCE($3, stock)
     WHERE id = $4
     RETURNING id, name, price, stock, created_at`,
    [name ?? null, price ?? null, stock ?? null, id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.delete("/api/products/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rowCount } = await pool.query("DELETE FROM products WHERE id = $1", [id]);
  if (!rowCount) return res.status(404).json({ error: "Not found" });
  res.status(204).send();
}));

app.get("/api/orders", asyncHandler(async (_req, res) => {
  const { rows } = await pool.query(
    `SELECT id, user_id, product_id, quantity, status, created_at
     FROM orders ORDER BY id`
  );
  res.json(rows);
}));

app.get("/api/orders/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rows } = await pool.query(
    `SELECT id, user_id, product_id, quantity, status, created_at
     FROM orders WHERE id = $1`,
    [id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.post("/api/orders", asyncHandler(async (req, res) => {
  const { user_id, product_id, quantity, status } = req.body || {};
  if (!user_id || !product_id) {
    return res.status(400).json({ error: "user_id and product_id required" });
  }
  const { rows } = await pool.query(
    `INSERT INTO orders (user_id, product_id, quantity, status)
     VALUES ($1, $2, $3, $4)
     RETURNING id, user_id, product_id, quantity, status, created_at`,
    [user_id, product_id, quantity ?? 1, status ?? "pending"]
  );
  res.status(201).json(rows[0]);
}));

app.put("/api/orders/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { user_id, product_id, quantity, status } = req.body || {};
  const { rows } = await pool.query(
    `UPDATE orders SET
       user_id = COALESCE($1, user_id),
       product_id = COALESCE($2, product_id),
       quantity = COALESCE($3, quantity),
       status = COALESCE($4, status)
     WHERE id = $5
     RETURNING id, user_id, product_id, quantity, status, created_at`,
    [user_id ?? null, product_id ?? null, quantity ?? null, status ?? null, id]
  );
  if (!rows[0]) return res.status(404).json({ error: "Not found" });
  res.json(rows[0]);
}));

app.delete("/api/orders/:id", asyncHandler(async (req, res) => {
  const id = Number(req.params.id);
  const { rowCount } = await pool.query("DELETE FROM orders WHERE id = $1", [id]);
  if (!rowCount) return res.status(404).json({ error: "Not found" });
  res.status(204).send();
}));

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: "Internal server error" });
});

const port = Number(process.env.PORT || 3000);
app.listen(port, () => {
  console.log(`Listening on ${port}`);
});

process.on("SIGINT", async () => {
  await pool.end();
  process.exit(0);
});
