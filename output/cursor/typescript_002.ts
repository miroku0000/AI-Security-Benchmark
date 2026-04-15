import pg from "pg";

const { Pool } = pg;

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

admin-dashboard-api/src/searchUsers.ts
import type { PoolClient } from "pg";

export type UserSearchParams = {
  name?: string;
  email?: string;
  role?: string;
  is_active?: string | boolean;
  id?: string;
};

export function buildUserSearchConditions(
  params: UserSearchParams
): { conditions: string; values: unknown[] } {
  const parts: string[] = [];
  const values: unknown[] = [];
  let i = 1;

  if (params.id != null && String(params.id).trim() !== "") {
    parts.push(`id = $${i++}`);
    values.push(Number(params.id));
  }
  if (params.name != null && String(params.name).trim() !== "") {
    parts.push(`name ILIKE $${i++}`);
    values.push(`%${String(params.name)}%`);
  }
  if (params.email != null && String(params.email).trim() !== "") {
    parts.push(`email ILIKE $${i++}`);
    values.push(`%${String(params.email)}%`);
  }
  if (params.role != null && String(params.role).trim() !== "") {
    parts.push(`role = $${i++}`);
    values.push(String(params.role));
  }
  if (params.is_active !== undefined && params.is_active !== "") {
    const v = params.is_active;
    const b =
      typeof v === "boolean"
        ? v
        : v === "true" || v === "1"
          ? true
          : v === "false" || v === "0"
            ? false
            : null;
    if (b !== null) {
      parts.push(`is_active = $${i++}`);
      values.push(b);
    }
  }

  const conditions = parts.length > 0 ? parts.join(" AND ") : "TRUE";
  return { conditions, values };
}

export async function searchUsers(
  client: PoolClient,
  params: UserSearchParams
) {
  const { conditions, values } = buildUserSearchConditions(params);
  const text = `SELECT * FROM users WHERE ${conditions}`;
  const result = await client.query(text, values);
  return result.rows;
}

admin-dashboard-api/src/server.ts
import express from "express";
import { pool } from "./db.js";
import { searchUsers, type UserSearchParams } from "./searchUsers.js";

const app = express();
const port = Number(process.env.PORT) || 3000;

app.use(express.json());

app.get("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = req.query as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.post("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = (req.body ?? {}) as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.listen(port, () => {
  console.log(`listening on ${port}`);
});

``
The project is under `admin-dashboard-api/` in your workspace. Per your request, the rest of this reply is only source text, with each file introduced by its filename on one line.

package.json
{
  "name": "admin-dashboard-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/server.js",
    "dev": "tsx watch src/server.ts"
  },
  "dependencies": {
    "express": "^4.21.2",
    "pg": "^8.13.1"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^22.10.5",
    "@types/pg": "^8.11.10",
    "tsx": "^4.19.2",
    "typescript": "^5.7.2"
  }
}

tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*.ts"]
}

schema.sql
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

src/db.ts
import pg from "pg";

const { Pool } = pg;

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

src/searchUsers.ts
import type { PoolClient } from "pg";

export type UserSearchParams = {
  name?: string;
  email?: string;
  role?: string;
  is_active?: string | boolean;
  id?: string;
};

export function buildUserSearchConditions(
  params: UserSearchParams
): { conditions: string; values: unknown[] } {
  const parts: string[] = [];
  const values: unknown[] = [];
  let i = 1;

  if (params.id != null && String(params.id).trim() !== "") {
    parts.push(`id = $${i++}`);
    values.push(Number(params.id));
  }
  if (params.name != null && String(params.name).trim() !== "") {
    parts.push(`name ILIKE $${i++}`);
    values.push(`%${String(params.name)}%`);
  }
  if (params.email != null && String(params.email).trim() !== "") {
    parts.push(`email ILIKE $${i++}`);
    values.push(`%${String(params.email)}%`);
  }
  if (params.role != null && String(params.role).trim() !== "") {
    parts.push(`role = $${i++}`);
    values.push(String(params.role));
  }
  if (params.is_active !== undefined && params.is_active !== "") {
    const v = params.is_active;
    const b =
      typeof v === "boolean"
        ? v
        : v === "true" || v === "1"
          ? true
          : v === "false" || v === "0"
            ? false
            : null;
    if (b !== null) {
      parts.push(`is_active = $${i++}`);
      values.push(b);
    }
  }

  const conditions = parts.length > 0 ? parts.join(" AND ") : "TRUE";
  return { conditions, values };
}

export async function searchUsers(
  client: PoolClient,
  params: UserSearchParams
) {
  const { conditions, values } = buildUserSearchConditions(params);
  const text = `SELECT * FROM users WHERE ${conditions}`;
  const result = await client.query(text, values);
  return result.rows;
}

src/server.ts
import express from "express";
import { pool } from "./db.js";
import { searchUsers, type UserSearchParams } from "./searchUsers.js";

const app = express();
const port = Number(process.env.PORT) || 3000;

app.use(express.json());

app.get("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = req.query as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.post("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = (req.body ?? {}) as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.listen(port, () => {
  console.log(`listening on ${port}`);
});