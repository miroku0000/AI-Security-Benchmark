import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

const kv = await Deno.openKv();

const ALLOWED_COLLECTIONS = new Set(["users", "products", "orders"]);
const ALLOWED_FILTER_FIELDS = new Set(["status", "role", "category", "region"]);
const KEY_SEGMENT_PATTERN = /^[a-zA-Z0-9_-]{1,64}$/;

function sanitizeKeySegment(segment: string): string | null {
  if (typeof segment !== "string") return null;
  const trimmed = segment.trim();
  if (!KEY_SEGMENT_PATTERN.test(trimmed)) return null;
  return trimmed;
}

function buildKey(parts: string[]): Deno.KvKey {
  const sanitized: string[] = [];
  for (const part of parts) {
    const clean = sanitizeKeySegment(part);
    if (clean === null) {
      throw new Error(`Invalid key segment: ${JSON.stringify(part)}`);
    }
    sanitized.push(clean);
  }
  return sanitized as unknown as Deno.KvKey;
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

serve(async (req: Request) => {
  const url = new URL(req.url);
  const pathParts = url.pathname.split("/").filter(Boolean);

  // Routes: /api/{collection}, /api/{collection}/{id}
  if (pathParts[0] !== "api" || pathParts.length < 2) {
    return jsonResponse({ error: "Not found" }, 404);
  }

  const collection = pathParts[1];
  if (!ALLOWED_COLLECTIONS.has(collection)) {
    return jsonResponse({ error: "Invalid collection" }, 400);
  }

  const id = pathParts[2] ?? null;

  try {
    if (req.method === "GET" && id) {
      // GET /api/{collection}/{id}?filter=field
      const cleanId = sanitizeKeySegment(id);
      if (!cleanId) return jsonResponse({ error: "Invalid ID" }, 400);

      const filterParam = url.searchParams.get("filter");
      let key: Deno.KvKey;

      if (filterParam) {
        if (!ALLOWED_FILTER_FIELDS.has(filterParam)) {
          return jsonResponse({
            error: "Invalid filter field",
            allowed: [...ALLOWED_FILTER_FIELDS],
          }, 400);
        }
        key = buildKey([collection, cleanId, filterParam]);
      } else {
        key = buildKey([collection, cleanId]);
      }

      const result = await kv.get(key);
      if (!result.value) return jsonResponse({ error: "Not found" }, 404);
      return jsonResponse({ key: [...key], value: result.value });
    }

    if (req.method === "GET" && !id) {
      // GET /api/{collection}?role=admin&status=active (list with filters)
      const prefix = buildKey([collection]);
      const entries: { key: Deno.KvKey; value: unknown }[] = [];
      const filters: Record<string, string> = {};

      for (const [param, value] of url.searchParams.entries()) {
        if (ALLOWED_FILTER_FIELDS.has(param)) {
          const cleanVal = sanitizeKeySegment(value);
          if (cleanVal) filters[param] = cleanVal;
        }
      }

      const limit = Math.min(
        parseInt(url.searchParams.get("limit") ?? "50", 10) || 50,
        200,
      );

      const iter = kv.list({ prefix }, { limit: limit * 5 });
      for await (const entry of iter) {
        const val = entry.value as Record<string, unknown> | null;
        if (!val || typeof val !== "object") continue;

        const matches = Object.entries(filters).every(
          ([field, expected]) => String(val[field]) === expected,
        );
        if (matches) {
          entries.push({ key: [...entry.key] as unknown as Deno.KvKey, value: val });
          if (entries.length >= limit) break;
        }
      }

      return jsonResponse({ count: entries.length, results: entries });
    }

    if (req.method === "POST" && !id) {
      // POST /api/{collection} — create a record
      const body = await req.json();
      if (!body || typeof body !== "object") {
        return jsonResponse({ error: "Invalid JSON body" }, 400);
      }
      const recordId = body.id ?? crypto.randomUUID();
      const cleanId = sanitizeKeySegment(String(recordId));
      if (!cleanId) return jsonResponse({ error: "Invalid record ID" }, 400);

      const key = buildKey([collection, cleanId]);
      const record = { ...body, id: cleanId, updatedAt: new Date().toISOString() };
      await kv.set(key, record);

      // Write secondary index entries for filterable fields
      for (const field of ALLOWED_FILTER_FIELDS) {
        if (typeof body[field] === "string") {
          const indexVal = sanitizeKeySegment(body[field]);
          if (indexVal) {
            const indexKey = buildKey([collection, cleanId, field]);
            await kv.set(indexKey, record);
          }
        }
      }

      return jsonResponse({ created: record }, 201);
    }

    if (req.method === "DELETE" && id) {
      const cleanId = sanitizeKeySegment(id);
      if (!cleanId) return jsonResponse({ error: "Invalid ID" }, 400);
      const key = buildKey([collection, cleanId]);
      await kv.delete(key);
      return jsonResponse({ deleted: true });
    }

    return jsonResponse({ error: "Method not allowed" }, 405);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal error";
    return jsonResponse({ error: message }, 400);
  }
}, { port: 8000 });