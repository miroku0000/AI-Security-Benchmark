export interface Env {
  PROCESSOR_SERVICE: Fetcher;
  DATA_SERVICE: Fetcher;
  ENVIRONMENT: string;
}

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
