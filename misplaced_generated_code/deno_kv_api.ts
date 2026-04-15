import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

const kv = await Deno.openKv();

async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const pathname = url.pathname;
  const method = req.method;

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    if (pathname.startsWith("/api/users") && method === "POST") {
      const body = await req.json();
      const userId = body.id || crypto.randomUUID();
      const userKey = ["users", userId];
      
      await kv.set(userKey, body);
      
      if (body.department) {
        await kv.set(["users", "by_department", body.department, userId], true);
      }
      if (body.role) {
        await kv.set(["users", "by_role", body.role, userId], true);
      }
      if (body.location) {
        await kv.set(["users", "by_location", body.location, userId], true);
      }
      if (body.status) {
        await kv.set(["users", "by_status", body.status, userId], true);
      }
      if (body.email) {
        await kv.set(["users", "by_email", body.email], userId);
      }
      
      return new Response(JSON.stringify({ id: userId, ...body }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 201,
      });
    }

    if (pathname.startsWith("/api/users/search") && method === "GET") {
      const params = url.searchParams;
      const results = [];
      
      if (params.has("department")) {
        const department = params.get("department");
        const keyPrefix = ["users", "by_department", department];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const userId = entry.key[3] as string;
          const userResult = await kv.get(["users", userId]);
          if (userResult.value) {
            results.push({ id: userId, ...userResult.value });
          }
        }
      } else if (params.has("role")) {
        const role = params.get("role");
        const keyPrefix = ["users", "by_role", role];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const userId = entry.key[3] as string;
          const userResult = await kv.get(["users", userId]);
          if (userResult.value) {
            results.push({ id: userId, ...userResult.value });
          }
        }
      } else if (params.has("location")) {
        const location = params.get("location");
        const keyPrefix = ["users", "by_location", location];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const userId = entry.key[3] as string;
          const userResult = await kv.get(["users", userId]);
          if (userResult.value) {
            results.push({ id: userId, ...userResult.value });
          }
        }
      } else if (params.has("status")) {
        const status = params.get("status");
        const keyPrefix = ["users", "by_status", status];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const userId = entry.key[3] as string;
          const userResult = await kv.get(["users", userId]);
          if (userResult.value) {
            results.push({ id: userId, ...userResult.value });
          }
        }
      } else if (params.has("email")) {
        const email = params.get("email");
        const userIdResult = await kv.get(["users", "by_email", email]);
        if (userIdResult.value) {
          const userResult = await kv.get(["users", userIdResult.value as string]);
          if (userResult.value) {
            results.push({ id: userIdResult.value, ...userResult.value });
          }
        }
      } else {
        const entries = kv.list({ prefix: ["users"] });
        for await (const entry of entries) {
          if (entry.key.length === 2 && entry.key[0] === "users") {
            results.push({ id: entry.key[1], ...entry.value });
          }
        }
      }
      
      return new Response(JSON.stringify(results), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (pathname.match(/^\/api\/users\/[^\/]+$/) && method === "GET") {
      const userId = pathname.split("/").pop();
      const result = await kv.get(["users", userId]);
      
      if (result.value) {
        return new Response(JSON.stringify({ id: userId, ...result.value }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      
      return new Response(JSON.stringify({ error: "User not found" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 404,
      });
    }

    if (pathname.match(/^\/api\/users\/[^\/]+$/) && method === "PUT") {
      const userId = pathname.split("/").pop();
      const body = await req.json();
      
      const existingResult = await kv.get(["users", userId]);
      if (existingResult.value) {
        const existing = existingResult.value as any;
        
        if (existing.department !== body.department) {
          if (existing.department) {
            await kv.delete(["users", "by_department", existing.department, userId]);
          }
          if (body.department) {
            await kv.set(["users", "by_department", body.department, userId], true);
          }
        }
        
        if (existing.role !== body.role) {
          if (existing.role) {
            await kv.delete(["users", "by_role", existing.role, userId]);
          }
          if (body.role) {
            await kv.set(["users", "by_role", body.role, userId], true);
          }
        }
        
        if (existing.location !== body.location) {
          if (existing.location) {
            await kv.delete(["users", "by_location", existing.location, userId]);
          }
          if (body.location) {
            await kv.set(["users", "by_location", body.location, userId], true);
          }
        }
        
        if (existing.status !== body.status) {
          if (existing.status) {
            await kv.delete(["users", "by_status", existing.status, userId]);
          }
          if (body.status) {
            await kv.set(["users", "by_status", body.status, userId], true);
          }
        }
        
        if (existing.email !== body.email) {
          if (existing.email) {
            await kv.delete(["users", "by_email", existing.email]);
          }
          if (body.email) {
            await kv.set(["users", "by_email", body.email], userId);
          }
        }
      }
      
      await kv.set(["users", userId], body);
      
      return new Response(JSON.stringify({ id: userId, ...body }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (pathname.match(/^\/api\/users\/[^\/]+$/) && method === "DELETE") {
      const userId = pathname.split("/").pop();
      
      const existingResult = await kv.get(["users", userId]);
      if (existingResult.value) {
        const existing = existingResult.value as any;
        
        if (existing.department) {
          await kv.delete(["users", "by_department", existing.department, userId]);
        }
        if (existing.role) {
          await kv.delete(["users", "by_role", existing.role, userId]);
        }
        if (existing.location) {
          await kv.delete(["users", "by_location", existing.location, userId]);
        }
        if (existing.status) {
          await kv.delete(["users", "by_status", existing.status, userId]);
        }
        if (existing.email) {
          await kv.delete(["users", "by_email", existing.email]);
        }
        
        await kv.delete(["users", userId]);
        
        return new Response(null, {
          headers: corsHeaders,
          status: 204,
        });
      }
      
      return new Response(JSON.stringify({ error: "User not found" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 404,
      });
    }

    if (pathname.startsWith("/api/products") && method === "POST") {
      const body = await req.json();
      const productId = body.id || crypto.randomUUID();
      const productKey = ["products", productId];
      
      await kv.set(productKey, body);
      
      if (body.category) {
        await kv.set(["products", "by_category", body.category, productId], true);
      }
      if (body.brand) {
        await kv.set(["products", "by_brand", body.brand, productId], true);
      }
      if (body.price) {
        const priceRange = Math.floor(body.price / 100) * 100;
        await kv.set(["products", "by_price_range", priceRange, productId], true);
      }
      if (body.sku) {
        await kv.set(["products", "by_sku", body.sku], productId);
      }
      
      return new Response(JSON.stringify({ id: productId, ...body }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 201,
      });
    }

    if (pathname.startsWith("/api/products/search") && method === "GET") {
      const params = url.searchParams;
      const results = [];
      
      if (params.has("category")) {
        const category = params.get("category");
        const keyPrefix = ["products", "by_category", category];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const productId = entry.key[3] as string;
          const productResult = await kv.get(["products", productId]);
          if (productResult.value) {
            results.push({ id: productId, ...productResult.value });
          }
        }
      } else if (params.has("brand")) {
        const brand = params.get("brand");
        const keyPrefix = ["products", "by_brand", brand];
        const entries = kv.list({ prefix: keyPrefix });
        
        for await (const entry of entries) {
          const productId = entry.key[3] as string;
          const productResult = await kv.get(["products", productId]);
          if (productResult.value) {
            results.push({ id: productId, ...productResult.value });
          }
        }
      } else if (params.has("min_price") || params.has("max_price")) {
        const minPrice = params.has("min_price") ? parseInt(params.get("min_price")) : 0;
        const maxPrice = params.has("max_price") ? parseInt(params.get("max_price")) : 999999;
        
        const minRange = Math.floor(minPrice / 100) * 100;
        const maxRange = Math.floor(maxPrice / 100) * 100;
        
        for (let range = minRange; range <= maxRange; range += 100) {
          const keyPrefix = ["products", "by_price_range", range];
          const entries = kv.list({ prefix: keyPrefix });
          
          for await (const entry of entries) {
            const productId = entry.key[3] as string;
            const productResult = await kv.get(["products", productId]);
            if (productResult.value) {
              const product = productResult.value as any;
              if (product.price >= minPrice && product.price <= maxPrice) {
                results.push({ id: productId, ...product });
              }
            }
          }
        }
      } else if (params.has("sku")) {
        const sku = params.get("sku");
        const productIdResult = await kv.get(["products", "by_sku", sku]);
        if (productIdResult.value) {
          const productResult = await kv.get(["products", productIdResult.value as string]);
          if (productResult.value) {
            results.push({ id: productIdResult.value, ...productResult.value });
          }
        }
      } else {
        const entries = kv.list({ prefix: ["products"] });
        for await (const entry of entries) {
          if (entry.key.length === 2 && entry.key[0] === "products") {
            results.push({ id: entry.key[1], ...entry.value });
          }
        }
      }
      
      return new Response(JSON.stringify(results), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (pathname.startswith("/api/analytics/aggregate") && method === "GET") {
      const params = url.searchParams;
      const collection = params.get("collection") || "users";
      const groupBy = params.get("group_by");
      
      if (!groupBy) {
        return new Response(JSON.stringify({ error: "group_by parameter required" }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 400,
        });
      }
      
      const aggregates = new Map();
      const keyPrefix = [collection, `by_${groupBy}`];
      const entries = kv.list({ prefix: keyPrefix });
      
      for await (const entry of entries) {
        const groupValue = entry.key[2] as string;
        const currentCount = aggregates.get(groupValue) || 0;
        aggregates.set(groupValue, currentCount + 1);
      }
      
      const results = Array.from(aggregates.entries()).map(([key, count]) => ({
        [groupBy]: key,
        count: count,
      }));
      
      return new Response(JSON.stringify(results), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (pathname === "/api/export" && method === "GET") {
      const params = url.searchParams;
      const collection = params.get("collection") || "users";
      const format = params.get("format") || "json";
      
      const results = [];
      const entries = kv.list({ prefix: [collection] });
      
      for await (const entry of entries) {
        if (entry.key.length === 2) {
          results.push({
            id: entry.key[1],
            ...entry.value as object,
          });
        }
      }
      
      if (format === "csv" && results.length > 0) {
        const headers = Object.keys(results[0]);
        const csvContent = [
          headers.join(","),
          ...results.map(row =>
            headers.map(header => {
              const value = row[header];
              return typeof value === "string" && value.includes(",")
                ? `"${value}"`
                : value;
            }).join(",")
          ),
        ].join("\n");
        
        return new Response(csvContent, {
          headers: {
            ...corsHeaders,
            "Content-Type": "text/csv",
            "Content-Disposition": `attachment; filename="${collection}.csv"`,
          },
        });
      }
      
      return new Response(JSON.stringify(results), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (pathname === "/api/batch" && method === "POST") {
      const body = await req.json();
      const operations = body.operations || [];
      const results = [];
      
      const atomic = kv.atomic();
      
      for (const op of operations) {
        if (op.type === "set") {
          const key = op.key.split(":");
          atomic.set(key, op.value);
          results.push({ status: "queued", operation: op });
        } else if (op.type === "delete") {
          const key = op.key.split(":");
          atomic.delete(key);
          results.push({ status: "queued", operation: op });
        }
      }
      
      await atomic.commit();
      
      return new Response(JSON.stringify({ results }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "Not found" }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 404,
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 500,
    });
  }
}

serve(handleRequest);