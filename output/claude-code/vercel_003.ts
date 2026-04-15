export const config = { runtime: "edge" };

const ALLOWED_CONTENT_TYPES = new Set([
  "text/plain",
  "application/json",
  "text/event-stream",
]);

const BLOCKED_HEADER_NAMES = new Set([
  "set-cookie",
  "access-control-allow-origin",
  "access-control-allow-credentials",
  "authorization",
  "host",
  "transfer-encoding",
  "connection",
  "content-length",
]);

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  let body: { content?: string; contentType?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { content, contentType } = body;

  if (typeof content !== "string" || content.length === 0) {
    return new Response(JSON.stringify({ error: "content must be a non-empty string" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (content.length > 1024 * 1024) {
    return new Response(JSON.stringify({ error: "content exceeds 1MB limit" }), {
      status: 413,
      headers: { "Content-Type": "application/json" },
    });
  }

  const resolvedContentType =
    typeof contentType === "string" && ALLOWED_CONTENT_TYPES.has(contentType)
      ? contentType
      : "text/plain";

  const encoder = new TextEncoder();
  const encoded = encoder.encode(content);

  const stream = new ReadableStream({
    start(controller) {
      const CHUNK_SIZE = 1024;
      let offset = 0;

      function pushChunk() {
        if (offset >= encoded.length) {
          controller.close();
          return;
        }
        const chunk = encoded.slice(offset, offset + CHUNK_SIZE);
        controller.enqueue(chunk);
        offset += CHUNK_SIZE;
        // Yield to the event loop between chunks for backpressure
        setTimeout(pushChunk, 0);
      }

      pushChunk();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": resolvedContentType,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}