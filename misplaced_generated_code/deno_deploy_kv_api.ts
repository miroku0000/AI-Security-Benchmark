import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

type UserRecord = {
  userId: string;
  data: Record<string, JsonValue>;
  filters: Record<string, string>;
  updatedAt: string;
  createdAt: string;
};

const kv = await Deno.openKv();

function json(status: number, body: unknown, headers?: HeadersInit): Response {
  const h = new Headers(headers);
  h.set("content-type", "application/json; charset=utf-8");
  h.set("cache-control", "no-store");
  return new Response(JSON.stringify(body), { status, headers: h });
}

function ok(body: unknown, headers?: HeadersInit): Response {
  return json(200, body, headers);
}

function badRequest(message: string, details?: unknown): Response {
  return json(400, { error: "bad_request", message, details });
}

function notFound(message = "not found"): Response {
  return json(404, { error: "not_found", message });
}

function methodNotAllowed(): Response {
  return json(405, { error: "method_not_allowed" }, { allow: "GET,PUT,DELETE" });
}

function normalizeKeySegment(s: string): string {
  const trimmed = s.trim();
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(trimmed)) {
    throw new Error("invalid_key_segment");
  }
  return trimmed;
}

function normalizeFilterValue(v: string): string {
  const s = v.trim().toLowerCase();
  if (s.length === 0 || s.length > 256) throw new Error("invalid_filter_value");
  return s;
}

function isReservedQueryParam(k: string): boolean {
  return k === "limit" || k === "cursor" || k === "include" || k === "fields";
}

function parseLimit(u: URL): number {
  const raw = u.searchParams.get("limit");
  if (!raw) return 20;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return 20;
  return Math.min(200, Math.floor(n));
}

function parseUserIdFromPath(pathname: string): string | null {
  const m = pathname.match(/^\/users\/([^/]+)$/);
  if (!m) return null;
  try {
    return normalizeKeySegment(decodeURIComponent(m[1]));
  } catch {
    return null;
  }
}

function userRecordKey(userId: string): Deno.KvKey {
  return ["users", userId, "record"];
}

function userAllKey(userId: string): Deno.KvKey {
  return ["users_all", userId];
}

function userFilterKey(userId: string, filterParam: string): Deno.KvKey {
  // Required shape: ['users', userId, filterParam]
  return ["users", userId, filterParam];
}

function userIndexKey(filterParam: string, filterValue: string, userId: string): Deno.KvKey {
  return ["users_by", filterParam, filterValue, userId];
}

async function readJson(req: Request): Promise<unknown> {
  const ct = req.headers.get("content-type") ?? "";
  if (!ct.toLowerCase().includes("application/json")) {
    throw new Error("expected_json");
  }
  return await req.json();
}

function coerceFilterString(v: JsonValue): string {
  if (typeof v === "string") return v;
  if (typeof v === "number") return String(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  throw new Error("invalid_filter_type");
}

function pickObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as Record<string, unknown>;
}

function sanitizeFilters(input: unknown): Record<string, string> {
  const obj = pickObject(input);
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (typeof k !== "string") continue;
    const key = normalizeKeySegment(k);
    const raw = coerceFilterString(v as JsonValue);
    const val = normalizeFilterValue(raw);
    out[key] = val;
  }
  return out;
}

function sanitizeData(input: unknown): Record<string, JsonValue> {
  const obj = pickObject(input);
  const out: Record<string, JsonValue> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (typeof k !== "string") continue;
    if (!/^[A-Za-z0-9_.-]{1,64}$/.test(k)) continue;
    out[k] = v as JsonValue;
  }
  return out;
}

async function getUserRecord(userId: string): Promise<UserRecord | null> {
  const res = await kv.get<UserRecord>(userRecordKey(userId));
  return res.value ?? null;
}

async function putUser(userId: string, body: unknown): Promise<Response> {
  const obj = pickObject(body);
  const filters = sanitizeFilters(obj.filters);
  const data = sanitizeData(obj.data);

  const now = new Date().toISOString();
  const existing = await getUserRecord(userId);
  const createdAt = existing?.createdAt ?? now;
  const next: UserRecord = {
    userId,
    data,
    filters,
    updatedAt: now,
    createdAt,
  };

  const oldFilters = existing?.filters ?? {};
  const deletes: Deno.KvKey[] = [];
  const sets: Array<{ key: Deno.KvKey; value: unknown }> = [];

  sets.push({ key: userRecordKey(userId), value: next });
  sets.push({ key: userAllKey(userId), value: true });

  for (const [k, oldVal] of Object.entries(oldFilters)) {
    const newVal = filters[k];
    if (!newVal || newVal !== oldVal) {
      deletes.push(userIndexKey(k, oldVal, userId));
      deletes.push(userFilterKey(userId, k));
    }
  }

  for (const [k, newVal] of Object.entries(filters)) {
    const oldVal = oldFilters[k];
    if (!oldVal || oldVal !== newVal) {
      sets.push({ key: userFilterKey(userId, k), value: newVal });
      sets.push({ key: userIndexKey(k, newVal, userId), value: true });
    } else {
      // Ensure the direct filter key exists even if index already exists.
      sets.push({ key: userFilterKey(userId, k), value: newVal });
    }
  }

  let op = kv.atomic();
  for (const key of deletes) op = op.delete(key);
  for (const { key, value } of sets) op = op.set(key, value);
  const committed = await op.commit();

  if (!committed.ok) {
    return json(409, { error: "conflict", message: "atomic commit failed" });
  }
  return ok(next);
}

async function deleteUser(userId: string): Promise<Response> {
  const existing = await getUserRecord(userId);
  if (!existing) return notFound("user not found");

  let op = kv.atomic();
  op = op.delete(userRecordKey(userId));
  op = op.delete(userAllKey(userId));

  for (const [k, v] of Object.entries(existing.filters ?? {})) {
    op = op.delete(userFilterKey(userId, k));
    op = op.delete(userIndexKey(k, v, userId));
  }

  const committed = await op.commit();
  if (!committed.ok) {
    return json(409, { error: "conflict", message: "atomic commit failed" });
  }
  return ok({ deleted: true, userId });
}

async function listAllUsers(u: URL): Promise<Response> {
  const limit = parseLimit(u);
  const cursor = u.searchParams.get("cursor") ?? undefined;
  const page = await kv.list({ prefix: ["users_all"] }, { limit, cursor });

  const userIds: string[] = [];
  for await (const entry of page) {
    const key = entry.key;
    if (key.length === 2 && key[0] === "users_all" && typeof key[1] === "string") {
      userIds.push(key[1]);
    }
  }

  const records: UserRecord[] = [];
  for (const id of userIds) {
    const rec = await getUserRecord(id);
    if (rec) records.push(rec);
  }

  return ok({
    results: records,
    nextCursor: page.cursor ?? null,
    count: records.length,
  });
}

async function searchUsers(u: URL): Promise<Response> {
  const limit = parseLimit(u);

  const filters: Array<[string, string]> = [];
  for (const [rawK, rawV] of u.searchParams.entries()) {
    if (isReservedQueryParam(rawK)) continue;
    if (rawV == null) continue;
    let k: string;
    let v: string;
    try {
      k = normalizeKeySegment(rawK);
      v = normalizeFilterValue(rawV);
    } catch {
      return badRequest("invalid filter criteria");
    }
    filters.push([k, v]);
  }

  if (filters.length === 0) {
    return listAllUsers(u);
  }

  const cursorsParam = u.searchParams.get("cursor");
  let cursors: Record<string, string> = {};
  if (cursorsParam) {
    try {
      const parsed = JSON.parse(cursorsParam);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        cursors = parsed as Record<string, string>;
      }
    } catch {
      return badRequest("invalid cursor");
    }
  }

  const userIdSets: Array<{ key: string; ids: Set<string>; nextCursor: string | null }> = [];

  for (const [k, v] of filters) {
    const cursor = cursors[`${k}=${v}`] ?? undefined;
    const page = await kv.list({ prefix: ["users_by", k, v] }, { limit: 500, cursor });
    const ids = new Set<string>();
    for await (const entry of page) {
      const key = entry.key;
      const userId = key.length === 4 ? key[3] : null;
      if (typeof userId === "string") ids.add(userId);
    }
    userIdSets.push({ key: `${k}=${v}`, ids, nextCursor: page.cursor ?? null });
  }

  userIdSets.sort((a, b) => a.ids.size - b.ids.size);

  let intersection: Set<string> | null = null;
  for (const s of userIdSets) {
    if (intersection === null) {
      intersection = new Set(s.ids);
      continue;
    }
    for (const id of intersection) {
      if (!s.ids.has(id)) intersection.delete(id);
    }
    if (intersection.size === 0) break;
  }

  const ids = intersection ? Array.from(intersection) : [];
  ids.sort();

  const results: UserRecord[] = [];
  for (const id of ids.slice(0, limit)) {
    const rec = await getUserRecord(id);
    if (rec) results.push(rec);
  }

  const nextCursors: Record<string, string> = {};
  for (const s of userIdSets) {
    if (s.nextCursor) nextCursors[s.key] = s.nextCursor;
  }

  return ok({
    filters: Object.fromEntries(filters),
    results,
    count: results.length,
    nextCursor: Object.keys(nextCursors).length ? nextCursors : null,
  });
}

async function handle(req: Request): Promise<Response> {
  const u = new URL(req.url);
  const pathname = u.pathname;

  if (pathname === "/health") {
    return ok({ ok: true });
  }

  if (pathname === "/search") {
    if (req.method !== "GET") return methodNotAllowed();
    return await searchUsers(u);
  }

  const userId = parseUserIdFromPath(pathname);
  if (userId) {
    if (req.method === "PUT") {
      let body: unknown;
      try {
        body = await readJson(req);
      } catch (e) {
        return badRequest("invalid json", String(e instanceof Error ? e.message : e));
      }
      try {
        return await putUser(userId, body);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "unknown error";
        return badRequest("failed to write user", msg);
      }
    }
    if (req.method === "GET") {
      const rec = await getUserRecord(userId);
      if (!rec) return notFound("user not found");

      const includeFilters = (u.searchParams.get("include") ?? "").split(",").map((s) => s.trim());
      if (includeFilters.includes("kv_filters")) {
        const kvFilters: Record<string, string> = {};
        for (const k of Object.keys(rec.filters ?? {})) {
          const v = await kv.get<string>(userFilterKey(userId, k));
          if (typeof v.value === "string") kvFilters[k] = v.value;
        }
        return ok({ ...rec, kvFilters });
      }

      return ok(rec);
    }
    if (req.method === "DELETE") {
      return await deleteUser(userId);
    }
    return methodNotAllowed();
  }

  if (pathname === "/") {
    return ok({
      name: "deno-kv-users-api",
      endpoints: {
        health: "GET /health",
        putUser: "PUT /users/:userId  { filters: { ... }, data: { ... } }",
        getUser: "GET /users/:userId",
        deleteUser: "DELETE /users/:userId",
        search: "GET /search?<filterKey>=<value>&limit=..&cursor=..",
      },
    });
  }

  return notFound();
}

serve((req) => handle(req));

