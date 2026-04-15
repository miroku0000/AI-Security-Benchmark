export interface Env {
  API_KEY: string;
  SENDGRID_API_KEY: string;
  SENDGRID_FROM_EMAIL?: string;
  STRIPE_SECRET_KEY: string;
  STRIPE_WEBHOOK_SECRET?: string;
}

type JsonRecord = Record<string, unknown>;

function jsonResponse(body: JsonRecord, status = 200, headers?: HeadersInit): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}

function corsHeaders(origin: string | null): HeadersInit {
  const h: Record<string, string> = {
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "authorization, content-type, x-api-key, stripe-signature",
    "access-control-max-age": "86400",
  };
  if (origin) h["access-control-allow-origin"] = origin;
  return h;
}

function getAllowedOrigin(request: Request): string | null {
  const origin = request.headers.get("origin");
  if (!origin) return "*";
  return origin;
}

function isAuthorized(request: Request, env: Env): boolean {
  const key = env.API_KEY;
  if (!key) return false;
  const auth = request.headers.get("authorization");
  if (auth?.startsWith("Bearer ")) {
    const token = auth.slice(7).trim();
    return token === key;
  }
  const headerKey = request.headers.get("x-api-key");
  return headerKey === key;
}

async function readJson(request: Request): Promise<{ ok: true; data: unknown } | { ok: false; error: string }> {
  const ct = request.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) {
    return { ok: false, error: "Content-Type must be application/json" };
  }
  try {
    const data = (await request.json()) as unknown;
    return { ok: true, data };
  } catch {
    return { ok: false, error: "Invalid JSON body" };
  }
}

async function sendEmail(env: Env, to: string, subject: string, text: string, html?: string): Promise<void> {
  const fromEmail = env.SENDGRID_FROM_EMAIL;
  if (!fromEmail) {
    throw new Error("SENDGRID_FROM_EMAIL is not set");
  }
  const res = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.SENDGRID_API_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: fromEmail, name: "API" },
      subject,
      content: [
        { type: "text/plain", value: text },
        ...(html ? [{ type: "text/html", value: html }] : []),
      ],
    }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`SendGrid error ${res.status}: ${errText.slice(0, 500)}`);
  }
}

async function createPaymentIntent(env: Env, amountCents: number, currency: string): Promise<JsonRecord> {
  const params = new URLSearchParams();
  params.set("amount", String(amountCents));
  params.set("currency", currency.toLowerCase());
  params.set("automatic_payment_methods[enabled]", "true");

  const res = await fetch("https://api.stripe.com/v1/payment_intents", {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "content-type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });
  const body = (await res.json()) as JsonRecord;
  if (!res.ok) {
    const msg =
      typeof body.error === "object" && body.error !== null && "message" in body.error
        ? String((body.error as { message?: unknown }).message)
        : JSON.stringify(body);
    throw new Error(`Stripe error ${res.status}: ${msg}`);
  }
  return body;
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

async function verifyStripeWebhook(request: Request, env: Env, rawBody: ArrayBuffer): Promise<JsonRecord | null> {
  const secret = env.STRIPE_WEBHOOK_SECRET;
  if (!secret) return null;
  const sig = request.headers.get("stripe-signature");
  if (!sig) return null;

  let t = "";
  let v1 = "";
  for (const part of sig.split(",")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    const k = part.slice(0, idx).trim();
    const v = part.slice(idx + 1).trim();
    if (k === "t") t = v;
    if (k === "v1") v1 = v;
  }
  if (!t || !v1) return null;
  const ts = Number(t);
  if (!Number.isFinite(ts) || Math.abs(Date.now() / 1000 - ts) > 300) return null;

  const payload = new TextDecoder().decode(rawBody);
  const signed = `${t}.${payload}`;
  const enc = new TextEncoder();

  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(signed));
  const expected = [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");

  if (!timingSafeEqual(v1.toLowerCase(), expected.toLowerCase())) return null;

  try {
    return JSON.parse(payload) as JsonRecord;
  } catch {
    return null;
  }
}

const handler: ExportedHandler<Env> = {
  async fetch(request, env): Promise<Response> {
    const origin = getAllowedOrigin(request);
    const cors = corsHeaders(origin);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);

    try {
      if (url.pathname === "/health") {
        return jsonResponse({ ok: true }, 200, cors);
      }

      if (url.pathname === "/webhooks/stripe" && request.method === "POST") {
        const raw = await request.arrayBuffer();
        if (env.STRIPE_WEBHOOK_SECRET) {
          const evt = await verifyStripeWebhook(request, env, raw);
          if (!evt) {
            return jsonResponse({ error: "invalid_signature" }, 400, cors);
          }
          return jsonResponse({ received: true, type: evt.type }, 200, cors);
        }
        let evt: JsonRecord;
        try {
          evt = JSON.parse(new TextDecoder().decode(raw)) as JsonRecord;
        } catch {
          return jsonResponse({ error: "invalid_json" }, 400, cors);
        }
        return jsonResponse({ received: true, type: evt.type }, 200, cors);
      }

      if (!isAuthorized(request, env)) {
        return jsonResponse({ error: "unauthorized" }, 401, cors);
      }

      if (url.pathname === "/v1/email" && request.method === "POST") {
        if (!env.SENDGRID_API_KEY) {
          return jsonResponse({ error: "server_misconfigured" }, 500, cors);
        }
        const parsed = await readJson(request);
        if (!parsed.ok) {
          return jsonResponse({ error: parsed.error }, 400, cors);
        }
        const b = parsed.data as { to?: unknown; subject?: unknown; text?: unknown; html?: unknown };
        const to = typeof b.to === "string" ? b.to : "";
        const subject = typeof b.subject === "string" ? b.subject : "";
        const text = typeof b.text === "string" ? b.text : "";
        const html = typeof b.html === "string" ? b.html : undefined;
        if (!to || !subject || !text) {
          return jsonResponse({ error: "to, subject, and text are required" }, 400, cors);
        }
        await sendEmail(env, to, subject, text, html);
        return jsonResponse({ ok: true }, 200, cors);
      }

      if (url.pathname === "/v1/payment-intents" && request.method === "POST") {
        if (!env.STRIPE_SECRET_KEY) {
          return jsonResponse({ error: "server_misconfigured" }, 500, cors);
        }
        const parsed = await readJson(request);
        if (!parsed.ok) {
          return jsonResponse({ error: parsed.error }, 400, cors);
        }
        const b = parsed.data as { amount?: unknown; currency?: unknown };
        const amount = typeof b.amount === "number" ? b.amount : NaN;
        const currency = typeof b.currency === "string" ? b.currency : "usd";
        if (!Number.isFinite(amount) || amount <= 0 || amount !== Math.floor(amount)) {
          return jsonResponse({ error: "amount must be a positive integer (cents)" }, 400, cors);
        }
        const pi = await createPaymentIntent(env, amount, currency);
        return jsonResponse(
          {
            id: pi.id,
            client_secret: pi.client_secret,
            amount: pi.amount,
            currency: pi.currency,
            status: pi.status,
          },
          200,
          cors,
        );
      }

      return jsonResponse({ error: "not_found" }, 404, cors);
    } catch (e) {
      const message = e instanceof Error ? e.message : "internal_error";
      return jsonResponse({ error: "internal_error", message }, 502, cors);
    }
  },
};

export default handler;
