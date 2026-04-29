import express, { Request, Response } from "express";
import { Pool } from "pg";

const pool = new Pool({
  host: process.env.DB_HOST || "localhost",
  port: parseInt(process.env.DB_PORT || "5432"),
  database: process.env.DB_NAME || "admin_dashboard",
  user: process.env.DB_USER || "postgres",
  password: process.env.DB_PASSWORD || "",
});

const app = express();
app.use(express.json());

app.get("/api/users/search", async (req: Request, res: Response) => {
  const { name, email, role, status, min_age, max_age, sort_by, order } =
    req.query;

  const conditions: string[] = [];
  const values: unknown[] = [];
  let paramIndex = 1;

  if (name) {
    conditions.push(`name ILIKE $${paramIndex++}`);
    values.push(`%${name}%`);
  }

  if (email) {
    conditions.push(`email ILIKE $${paramIndex++}`);
    values.push(`%${email}%`);
  }

  if (role) {
    conditions.push(`role = $${paramIndex++}`);
    values.push(role);
  }

  if (status) {
    conditions.push(`status = $${paramIndex++}`);
    values.push(status);
  }

  if (min_age) {
    conditions.push(`age >= $${paramIndex++}`);
    values.push(parseInt(min_age as string));
  }

  if (max_age) {
    conditions.push(`age <= $${paramIndex++}`);
    values.push(parseInt(max_age as string));
  }

  const whereClause =
    conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  const allowedSortColumns = [
    "name",
    "email",
    "role",
    "status",
    "age",
    "created_at",
  ];
  const sortColumn = allowedSortColumns.includes(sort_by as string)
    ? (sort_by as string)
    : "created_at";
  const sortOrder = order === "asc" ? "ASC" : "DESC";

  const query = `SELECT id, name, email, role, status, age, created_at FROM users ${whereClause} ORDER BY ${sortColumn} ${sortOrder} LIMIT 100`;

  try {
    const client = await pool.connect();
    try {
      const result = await client.query(query, values);
      res.json({ users: result.rows, count: result.rowCount });
    } finally {
      client.release();
    }
  } catch (err) {
    console.error("Search query failed:", err);
    res.status(500).json({ error: "Search failed" });
  }
});

app.get("/api/users/:id", async (req: Request, res: Response) => {
  const { id } = req.params;

  try {
    const client = await pool.connect();
    try {
      const result = await client.query(
        "SELECT id, name, email, role, status, age, created_at FROM users WHERE id = $1",
        [id]
      );
      if (result.rows.length === 0) {
        res.status(404).json({ error: "User not found" });
        return;
      }
      res.json({ user: result.rows[0] });
    } finally {
      client.release();
    }
  } catch (err) {
    console.error("User fetch failed:", err);
    res.status(500).json({ error: "Fetch failed" });
  }
});

const PORT = parseInt(process.env.PORT || "3000");
app.listen(PORT, () => {
  console.log(`Admin dashboard API running on port ${PORT}`);
});