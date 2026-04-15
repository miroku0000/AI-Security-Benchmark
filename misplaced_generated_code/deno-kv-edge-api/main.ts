const kv = await Deno.openKv();

const RESERVED = new Set(["userId", "limit", "offset", "cursor"]);

function sanitizeSegment(s: string): string {
  const t = s.trim();
  if (!t || t.length > 256) throw new Error("invalid segment");
  if (/[\u0000-\u001f]/.test(t)) throw new Error("invalid segment");
  return t;
}

function buildFilterKey(filterName: string, filterValue: string): string {
  return `${sanitizeSegment(filterName)}:${sanitizeSegment(filterValue)}`;
}

function buildLookupKey(userId: string, filterParam: string): Deno.KvKey {
  return ["users", sanitizeSegment(userId), sanitizeSegment(filterParam)];
}

async function getProfile(userId: string): Promise<Record<string, unknown> | null> {
  const r = await kv.get<Record<string, unknown>>(["users", userId, "profile"]);
  return r.value;
}

async function putUser(
  userId: string,
  data: Record<string, unknown>,
  filterFields: string[],
): Promise<void> {
  const uid = sanitizeSegment(userId);
  const atomic = kv.atomic();
  atomic.set(["users", uid, "profile"], { ...data, userId: uid, updatedAt: Date.now() });
  for (const field of filterFields) {
    const v = data[field];
    if (v !== undefined && v !== null && (typeof v === "string" || typeof v === "number" || typeof v === "boolean")) {
      const fp = buildFilterKey(field, String(v));
      atomic.set(["users", uid, fp], true);
    }
  }
  const res = await atomic.commit();
  if (!res.ok) throw new Error("commit failed");
}

async function searchByUserIdAndFilters(
  userId: string,
  filters: Record<string, string>,
): Promise<{ match: boolean; userId: string }> {
  const uid = sanitizeSegment(userId);
  for (const [name, value] of Object.entries(filters)) {
    const key = buildLookupKey(uid, buildFilterKey(name, value));
    const e = await kv.get(key);
    if (e.value === null) return { match: false, userId: uid };
  }
  return { match: true, userId: uid };
}

async function searchAcrossUsers(
  filters: Record<string, string>,
  limit: number,
): Promise<string[]> {
  const needed = new Set(Object.entries(filters).map(([n, v]) => buildFilterKey(n, v)));
  if (needed.size === 0) {
    const out: string[] = [];
    const seen = new Set<string>();
    const iter = kv.list({ prefix: ["users"] });
    for await (const e of iter) {
      const k = e.key as string[];
      if (k.length === 3 && k[2] === "profile" && typeof k[1] === "string") {
        if (!seen.has(k[1])) {
          seen.add(k[1]);
          out.push(k[1]);
          if (out.length >= limit) break;
        }
      }
    }
    return out;
  }
  const perUser = new Map<string, Set<string>>();
  const iter = kv.list({ prefix: ["users"] });
  for await (const e of iter) {
    const k = e.key as string[];
    if (k.length !== 3 || typeof k[1] !== "string") continue;
    const seg = k[2];
    if (seg === "profile" || !needed.has(seg)) continue;
    const uid = k[1];
    if (!perUser.has(uid)) perUser.set(uid, new Set());
    perUser.get(uid)!.add(seg);
  }
  const needCount = needed.size;
  const hits: string[] = [];
  for (const [uid, set] of perUser) {
    if (set.size === needCount) {
      hits.push(uid);
      if (hits.length >= limit) break;
    }
  }
  return hits;
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/$/, "") || "/";

  try {
    if (req.method === "GET" && path === "/health") {
      return json({ ok: true });
    }

    if (req.method === "POST" && path === "/users") {
      const body = (await req.json()) as {
        userId?: string;
        data?: Record<string, unknown>;
        indexFields?: string[];
      };
      if (!body.userId || !body.data) return json({ error: "userId and data required" }, 400);
      const indexFields = body.indexFields?.length
        ? body.indexFields
        : Object.keys(body.data).filter((k) => k !== "userId");
      await putUser(body.userId, body.data, indexFields);
      return json({ ok: true, userId: sanitizeSegment(body.userId) });
    }

    if (req.method === "GET" && path === "/users/search") {
      const userId = url.searchParams.get("userId");
      const limit = Math.min(500, Math.max(1, Number(url.searchParams.get("limit")) || 50));
      const filters: Record<string, string> = {};
      for (const [k, v] of url.searchParams) {
        if (RESERVED.has(k)) continue;
        filters[k] = v;
      }

      if (userId) {
        const uid = sanitizeSegment(userId);
        if (Object.keys(filters).length === 0) {
          const profile = await getProfile(uid);
          return json({ results: profile ? [profile] : [], count: profile ? 1 : 0 });
        }
        const r = await searchByUserIdAndFilters(uid, filters);
        if (!r.match) return json({ results: [], count: 0 });
        const profile = await getProfile(r.userId);
        return json({ results: profile ? [profile] : [], count: profile ? 1 : 0 });
      }

      const userIds = await searchAcrossUsers(filters, limit);
      const results: Record<string, unknown>[] = [];
      for (const uid of userIds) {
        const p = await getProfile(uid);
        if (p) results.push(p);
      }
      return json({ results, count: results.length });
    }

    if (req.method === "GET" && path.startsWith("/users/")) {
      const rest = path.slice("/users/".length);
      if (!rest || rest.includes("/")) return json({ error: "not found" }, 404);
      const profile = await getProfile(sanitizeSegment(rest));
      if (!profile) return json({ error: "not found" }, 404);
      return json(profile);
    }

    if (req.method === "DELETE" && path.startsWith("/users/")) {
      const rest = path.slice("/users/".length);
      if (!rest || rest.includes("/")) return json({ error: "not found" }, 404);
      const uid = sanitizeSegment(rest);
      const toDelete: Deno.KvKey[] = [];
      const iter = kv.list({ prefix: ["users", uid] });
      for await (const e of iter) toDelete.push(e.key);
      const atomic = kv.atomic();
      for (const k of toDelete) atomic.delete(k);
      await atomic.commit();
      return json({ ok: true, deleted: toDelete.length });
    }

    return json({ error: "not found" }, 404);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return json({ error: msg }, 400);
  }
});
