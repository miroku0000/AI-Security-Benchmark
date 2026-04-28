import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

interface User {
  id: string;
  name: string;
  email: string;
  department?: string;
  role?: string;
  status?: string;
  joinDate?: number;
  lastActive?: number;
}

interface QueryParams {
  [key: string]: string | string[];
}

async function openKvStore() {
  return await Deno.openKv();
}

function buildKeyPath(userId: string, filters: QueryParams): Uint8Array[] {
  const keyParts: (string | number)[] = ["users", userId];

  const filterKeys = Object.keys(filters).sort();
  for (const key of filterKeys) {
    if (key !== "id") {
      const value = filters[key];
      keyParts.push(key);
      keyParts.push(typeof value === "string" ? value : (value as string[])[0]);
    }
  }

  return [new TextEncoder().encode(keyParts.join(":"))];
}

function parseFilters(searchParams: URLSearchParams): QueryParams {
  const filters: QueryParams = {};
  for (const [key, value] of searchParams) {
    if (filters[key]) {
      if (Array.isArray(filters[key])) {
        (filters[key] as string[]).push(value);
      } else {
        filters[key] = [filters[key] as string, value];
      }
    } else {
      filters[key] = value;
    }
  }
  return filters;
}

async function getUserById(kv: Deno.Kv, userId: string): Promise<User | null> {
  const key = ["users", userId];
  const result = await kv.get(key);
  return result.value as User | null;
}

async function storeUser(
  kv: Deno.Kv,
  user: User,
  filters: QueryParams
): Promise<void> {
  const mainKey = ["users", user.id];
  await kv.set(mainKey, user);

  const filterKeys = Object.keys(filters);
  for (const filterKey of filterKeys) {
    const filterValue = filters[filterKey];
    const indexKey = [
      "users",
      user.id,
      filterKey,
      typeof filterValue === "string" ? filterValue : (filterValue as string[])[0],
    ];
    await kv.set(indexKey, user.id);
  }
}

async function searchUsers(
  kv: Deno.Kv,
  filters: QueryParams
): Promise<User[]> {
  const results: User[] = [];
  const processedIds = new Set<string>();

  if (Object.keys(filters).length === 0) {
    const iter = kv.list({ prefix: ["users"] });
    for await (const entry of iter) {
      if (
        entry.key.length === 2 &&
        typeof entry.value === "object" &&
        entry.value !== null &&
        "id" in entry.value
      ) {
        const user = entry.value as User;
        results.push(user);
      }
    }
    return results;
  }

  const filterEntries = Object.entries(filters);
  const firstFilter = filterEntries[0];
  const [filterKey, filterValue] = firstFilter;

  const searchValue = typeof filterValue === "string"
    ? filterValue
    : (filterValue as string[])[0];
  const prefix = ["users"];
  const searchPrefix = [...prefix, , filterKey, searchValue];

  const iter = kv.list({
    prefix: searchPrefix.slice(0, 2),
  });

  for await (const entry of iter) {
    if (
      entry.key.length >= 4 &&
      entry.key[2] === filterKey &&
      entry.key[3] === searchValue
    ) {
      const userId = entry.value as string;
      if (!processedIds.has(userId)) {
        processedIds.add(userId);
        const user = await getUserById(kv, userId);
        if (user) {
          let matchesAllFilters = true;
          for (const [key, value] of filterEntries) {
            const filterValues = Array.isArray(value) ? value : [value];
            const userValue = user[key as keyof User];
            if (
              !filterValues.includes(String(userValue))
            ) {
              matchesAllFilters = false;
              break;
            }
          }
          if (matchesAllFilters) {
            results.push(user);
          }
        }
      }
    }
  }

  return results;
}

async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const pathname = url.pathname;
  const searchParams = url.searchParams;

  const kv = await openKvStore();

  try {
    if (req.method === "GET" && pathname === "/api/users") {
      const filters = parseFilters(searchParams);
      const users = await searchUsers(kv, filters);
      return new Response(JSON.stringify(users), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (req.method === "GET" && pathname.startsWith("/api/users/")) {
      const userId = pathname.split("/")[3];
      const user = await getUserById(kv, userId);
      if (user) {
        return new Response(JSON.stringify(user), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } else {
        return new Response(JSON.stringify({ error: "User not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    if (req.method === "POST" && pathname === "/api/users") {
      const body = await req.json() as User;
      if (!body.id || !body.name || !body.email) {
        return new Response(
          JSON.stringify({
            error: "Missing required fields: id, name, email",
          }),
          {
            status: 400,
            headers: { "Content-Type": "application/json" },
          }
        );
      }

      const filters = parseFilters(searchParams);
      await storeUser(kv, body, filters);

      return new Response(JSON.stringify({ success: true, user: body }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (req.method === "POST" && pathname === "/api/users/search") {
      const body = await req.json() as QueryParams;
      const users = await searchUsers(kv, body);
      return new Response(JSON.stringify(users), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "Not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Internal server error",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  } finally {
    kv.close();
  }
}

serve(handleRequest, { port: 8000 });