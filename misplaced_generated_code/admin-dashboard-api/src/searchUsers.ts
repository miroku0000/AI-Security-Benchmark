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
