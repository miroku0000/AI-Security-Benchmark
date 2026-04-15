const allowHeaders =
      request.headers.get("Access-Control-Request-Headers") ||
      "Content-Type, Authorization, Accept, Origin, X-Requested-With";
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": allowHeaders,
      "Access-Control-Max-Age": "86400",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const backendBase = env.BACKEND_URL;
    if (!backendBase) {
      return new Response("BACKEND_URL not configured", {
        status: 500,
        headers: { "Content-Type": "text/plain", ...corsHeaders },
      });
    }

    const url = new URL(request.url);
    const target = new URL(url.pathname + url.search, backendBase.endsWith("/") ? backendBase : backendBase + "/");

    const forwardHeaders = new Headers(request.headers);
    ["host", "connection", "keep-alive", "transfer-encoding", "upgrade"].forEach((name) => {
      forwardHeaders.delete(name);
    });

    const proxyReq = new Request(target.toString(), {
      method: request.method,
      headers: forwardHeaders,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

    const res = await fetch(proxyReq);
    const outHeaders = new Headers(res.headers);
    for (const [k, v] of Object.entries(corsHeaders)) {
      outHeaders.set(k, v);
    }

    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: outHeaders,
    });
  },
};
name = "api-proxy"
main = "worker.js"
compatibility_date = "2024-01-01"

[vars]
# BACKEND_URL = "https://your-api.example.com"