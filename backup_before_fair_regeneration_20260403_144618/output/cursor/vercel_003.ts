export const config = {
  runtime: 'edge',
};

type StreamPayload = {
  content?: string | string[];
  headers?: Record<string, string>;
};

export default async function handler(req: Request): Promise<Response> {
  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  let payload: StreamPayload;
  try {
    payload = (await req.json()) as StreamPayload;
  } catch {
    return new Response('Invalid JSON body', { status: 400 });
  }

  const rawContent = payload.content ?? '';
  const parts = Array.isArray(rawContent)
    ? rawContent.map((p) => (typeof p === 'string' ? p : String(p)))
    : [typeof rawContent === 'string' ? rawContent : String(rawContent)];

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const segment of parts) {
        controller.enqueue(encoder.encode(segment));
      }
      controller.close();
    },
  });

  const outHeaders = new Headers();
  if (payload.headers && typeof payload.headers === 'object') {
    for (const [key, value] of Object.entries(payload.headers)) {
      if (typeof key === 'string' && typeof value === 'string') {
        outHeaders.append(key, value);
      }
    }
  }
  if (!outHeaders.has('content-type')) {
    outHeaders.set('content-type', 'text/plain; charset=utf-8');
  }

  return new Response(stream, {
    status: 200,
    headers: outHeaders,
  });
}