const USER_PREFIX = "user:";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

function timingSafeEqual(a: string, b: string): boolean {
  const ae = new TextEncoder().encode(a);
  const be = new TextEncoder().encode(b);
  if (ae.length !== be.length) return false;
  let out = 0;
  for (let i = 0; i < ae.length; i++) out |= ae[i] ^ be[i];
  return out === 0;
}

async function pbkdf2Hash(password: string, salt: Uint8Array): Promise<string> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      salt,
      iterations: 210_000,
      hash: "SHA-256",
    },
    keyMaterial,
    256
  );
  return btoa(String.fromCharCode(...new Uint8Array(bits)));
}

function randomToken(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    if (request.method !== "POST") {
      return jsonResponse({ error: "method_not_allowed" }, 405);
    }

    const url = new URL(request.url);
    if (url.pathname !== "/auth/login" && url.pathname !== "/login") {
      return jsonResponse({ error: "not_found" }, 404);
    }

    let body: LoginBody;
    try {
      body = (await request.json()) as LoginBody;
    } catch {
      return jsonResponse({ error: "invalid_json" }, 400);
    }

    const username = typeof body.username === "string" ? body.username.trim() : "";
    const password = typeof body.password === "string" ? body.password : "";

    if (!username || !password) {
      return jsonResponse({ error: "username_and_password_required" }, 400);
    }

    const raw = await env.USERS.get(`${USER_PREFIX}${username}`);
    if (!raw) {
      await pbkdf2Hash(password, crypto.getRandomValues(new Uint8Array(16)));
      return jsonResponse({ error: "invalid_credentials" }, 401);
    }

    let record: UserRecord;
    try {
      record = JSON.parse(raw) as UserRecord;
    } catch {
      return jsonResponse({ error: "user_record_invalid" }, 500);
    }

    let salt: Uint8Array;
    try {
      const bin = atob(record.saltB64);
      salt = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) salt[i] = bin.charCodeAt(i);
    } catch {
      return jsonResponse({ error: "user_record_invalid" }, 500);
    }

    const computed = await pbkdf2Hash(password, salt);
    if (!timingSafeEqual(computed, record.hashB64)) {
      return jsonResponse({ error: "invalid_credentials" }, 401);
    }

    const sessionToken = randomToken();
    const ttl = Math.max(
      60,
      parseInt(env.SESSION_TTL_SECONDS ?? "86400", 10) || 86400
    );

    await env.SESSIONS.put(
      `session:${sessionToken}`,
      JSON.stringify({ username, created_at: Date.now() }),
      { expirationTtl: ttl }
    );

    return jsonResponse({
      session_token: sessionToken,
      expires_in_seconds: ttl,
      token_type: "Bearer",
    });
  },
};