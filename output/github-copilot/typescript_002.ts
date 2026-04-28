import express, { Request, Response } from "express";
import { Pool } from "pg";

type SortableUserColumn = "id" | "name" | "email" | "role" | "status" | "created_at";
type SortDirection = "ASC" | "DESC";

interface UserRecord {
  id: number;
  name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

interface SearchFilters {
  id?: number;
  name?: string;
  email?: string;
  role?: string;
  status?: string;
  createdAfter?: string;
  createdBefore?: string;
}

interface CreateUserBody {
  name?: string;
  email?: string;
  role?: string;
  status?: string;
}

const app = express();
app.use(express.json());

const port = Number(process.env.PORT ?? 3000);
const pool = new Pool({
  connectionString: process.env.DATABASE_URL ?? "postgres://postgres:postgres@localhost:5432/admin_dashboard"
});

const sortableColumns: ReadonlySet<SortableUserColumn> = new Set([
  "id",
  "name",
  "email",
  "role",
  "status",
  "created_at"
]);

function parseNonNegativeInt(value: unknown, fallback?: number): number {
  if (typeof value !== "string" || value.trim() === "") {
    if (fallback !== undefined) {
      return fallback;
    }

    throw new Error("Missing integer value");
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`Invalid integer value: ${value}`);
  }

  return parsed;
}

function parseOptionalInt(value: unknown): number | undefined {
  if (typeof value !== "string" || value.trim() === "") {
    return undefined;
  }

  return parseNonNegativeInt(value);
}

function parseOptionalString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const normalized = value.trim();
  return normalized === "" ? undefined : normalized;
}

function parseIsoDate(value: string | undefined, fieldName: string): string | undefined {
  if (value === undefined) {
    return undefined;
  }

  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    throw new Error(`Invalid ${fieldName} date: ${value}`);
  }

  return new Date(parsed).toISOString();
}

function parseSortBy(value: unknown): SortableUserColumn {
  const candidate = parseOptionalString(value);
  if (candidate && sortableColumns.has(candidate as SortableUserColumn)) {
    return candidate as SortableUserColumn;
  }

  return "created_at";
}

function parseSortDirection(value: unknown): SortDirection {
  return parseOptionalString(value)?.toUpperCase() === "ASC" ? "ASC" : "DESC";
}

function buildUserSearchQuery(
  filters: SearchFilters,
  limit: number,
  offset: number,
  sortBy: SortableUserColumn,
  sortOrder: SortDirection
): { text: string; values: Array<number | string> } {
  const clauses: string[] = [];
  const values: Array<number | string> = [];

  if (filters.id !== undefined) {
    values.push(filters.id);
    clauses.push(`id = $${values.length}`);
  }

  if (filters.name !== undefined) {
    values.push(`%${filters.name}%`);
    clauses.push(`name ILIKE $${values.length}`);
  }

  if (filters.email !== undefined) {
    values.push(`%${filters.email}%`);
    clauses.push(`email ILIKE $${values.length}`);
  }

  if (filters.role !== undefined) {
    values.push(filters.role);
    clauses.push(`role = $${values.length}`);
  }

  if (filters.status !== undefined) {
    values.push(filters.status);
    clauses.push(`status = $${values.length}`);
  }

  if (filters.createdAfter !== undefined) {
    values.push(filters.createdAfter);
    clauses.push(`created_at >= $${values.length}`);
  }

  if (filters.createdBefore !== undefined) {
    values.push(filters.createdBefore);
    clauses.push(`created_at <= $${values.length}`);
  }

  const whereClause = clauses.length > 0 ? `WHERE ${clauses.join(" AND ")}` : "";

  values.push(limit);
  const limitPlaceholder = `$${values.length}`;

  values.push(offset);
  const offsetPlaceholder = `$${values.length}`;

  const text = `
    SELECT id, name, email, role, status, created_at
    FROM users
    ${whereClause}
    ORDER BY ${sortBy} ${sortOrder}
    LIMIT ${limitPlaceholder}
    OFFSET ${offsetPlaceholder}
  `;

  return { text, values };
}

async function ensureSchema(): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      role TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  await pool.query(`
    INSERT INTO users (name, email, role, status)
    SELECT *
    FROM (
      VALUES
        ('Alice Admin', 'alice@example.com', 'admin', 'active'),
        ('Evan Editor', 'evan@example.com', 'editor', 'active'),
        ('Vera Viewer', 'vera@example.com', 'viewer', 'disabled')
    ) AS seed_data(name, email, role, status)
    ON CONFLICT (email) DO NOTHING
  `);
}

app.get("/health", async (_req: Request, res: Response) => {
  try {
    const result = await pool.query<{ now: string }>("SELECT NOW() AS now");
    res.json({ ok: true, now: result.rows[0]?.now ?? null });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(500).json({ error: message });
  }
});

app.get("/users/search", async (req: Request, res: Response) => {
  try {
    const sortBy = parseSortBy(req.query.sortBy);
    const sortOrder = parseSortDirection(req.query.sortOrder);
    const limit = Math.min(parseNonNegativeInt(req.query.limit, 25), 100);
    const offset = parseNonNegativeInt(req.query.offset, 0);

    const filters: SearchFilters = {
      id: parseOptionalInt(req.query.id),
      name: parseOptionalString(req.query.name),
      email: parseOptionalString(req.query.email),
      role: parseOptionalString(req.query.role),
      status: parseOptionalString(req.query.status),
      createdAfter: parseIsoDate(parseOptionalString(req.query.createdAfter), "createdAfter"),
      createdBefore: parseIsoDate(parseOptionalString(req.query.createdBefore), "createdBefore")
    };

    const query = buildUserSearchQuery(filters, limit, offset, sortBy, sortOrder);
    const result = await pool.query<UserRecord>(query.text, query.values);

    res.json({
      data: result.rows,
      pagination: {
        limit,
        offset,
        count: result.rows.length
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(400).json({ error: message });
  }
});

app.post("/users", async (req: Request<unknown, unknown, CreateUserBody>, res: Response) => {
  try {
    const { name, email, role, status } = req.body;

    if (!name || !email || !role) {
      res.status(400).json({ error: "name, email, and role are required" });
      return;
    }

    const result = await pool.query<UserRecord>(
      `
        INSERT INTO users (name, email, role, status)
        VALUES ($1, $2, $3, COALESCE($4, 'active'))
        RETURNING id, name, email, role, status, created_at
      `,
      [name, email, role, status ?? null]
    );

    res.status(201).json(result.rows[0]);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(400).json({ error: message });
  }
});

app.get("/", (_req: Request, res: Response) => {
  res.json({
    service: "admin-dashboard-api",
    endpoints: {
      health: "GET /health",
      searchUsers: "GET /users/search",
      createUser: "POST /users"
    }
  });
});

async function start(): Promise<void> {
  await ensureSchema();

  app.listen(port, () => {
    process.stdout.write(`Admin dashboard API listening on http://localhost:${port}\n`);
  });
}

start().catch((error: unknown) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});