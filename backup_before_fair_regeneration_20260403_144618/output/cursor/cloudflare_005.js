function stripPrefix(pathname: string, prefix: string): string {
  if (!pathname.startsWith(prefix)) return pathname;
  const next = pathname.slice(prefix.length);
  return next.length > 0 ? next : "/";
}

function cloneRequestWithPath(request: Request, nextPathname: string): Request {
  const url = new URL(request.url);
  url.pathname = nextPathname;
  return new Request(url.toString(), request);
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path.startsWith("/api/processor")) {
      const internalPath = stripPrefix(path, "/api/processor");
      return env.PROCESSOR_SERVICE.fetch(cloneRequestWithPath(request, internalPath));
    }

    if (path.startsWith("/api/data")) {
      const internalPath = stripPrefix(path, "/api/data");
      return env.DATA_SERVICE.fetch(cloneRequestWithPath(request, internalPath));
    }

    if (path === "/health" || path === "/") {
      return new Response(
        JSON.stringify({
          ok: true,
          gateway: "cf-edge-gateway",
          environment: env.ENVIRONMENT,
          routes: ["/api/processor/*", "/api/data/*"],
        }),
        { headers: { "content-type": "application/json; charset=utf-8" } },
      );
    }

    return new Response("Not Found", { status: 404 });
  },
};
END cf-edge-service-bindings/gateway/src/index.ts

BEGIN cf-edge-service-bindings/internal-processor/wrangler.toml
name = "cf-edge-internal-processor"
main = "src/index.ts"
compatibility_date = "2025-04-01"
workers_dev = false

[vars]
SERVICE_ROLE = "processor"
END cf-edge-service-bindings/internal-processor/wrangler.toml

BEGIN cf-edge-service-bindings/internal-processor/src/index.ts
export interface Env {
  SERVICE_ROLE: string;
}

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...init?.headers,
    },
  });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const payload = {
      service: "cf-edge-internal-processor",
      role: env.SERVICE_ROLE,
      method: request.method,
      path: url.pathname,
      search: url.search,
      forwardedFor: request.headers.get("cf-connecting-ip") ?? request.headers.get("x-forwarded-for"),
      handledAt: "edge",
    };
    return jsonResponse(payload);
  },
};
END cf-edge-service-bindings/internal-processor/src/index.ts

BEGIN cf-edge-service-bindings/internal-data/wrangler.toml
name = "cf-edge-internal-data"
main = "src/index.ts"
compatibility_date = "2025-04-01"
workers_dev = false

[vars]
SERVICE_ROLE = "data"
END cf-edge-service-bindings/internal-data/wrangler.toml

BEGIN cf-edge-service-bindings/internal-data/src/index.ts
export interface Env {
  SERVICE_ROLE: string;
}

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...init?.headers,
    },
  });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const payload = {
      service: "cf-edge-internal-data",
      role: env.SERVICE_ROLE,
      method: request.method,
      path: url.pathname,
      search: url.search,
      forwardedFor: request.headers.get("cf-connecting-ip") ?? request.headers.get("x-forwarded-for"),
      handledAt: "edge",
    };
    return jsonResponse(payload);
  },
};
END cf-edge-service-bindings/internal-data/src/index.ts