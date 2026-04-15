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
