import express from "express";
import { createRemoteJWKSet, jwtVerify } from "jose";

const PORT = Number(process.env.PORT) || 3000;
const ISSUER = process.env.OAUTH_ISSUER;
const AUDIENCE = process.env.OAUTH_AUDIENCE;
const JWKS_URI = process.env.OAUTH_JWKS_URI;
const CLOCK_TOLERANCE = process.env.OAUTH_CLOCK_TOLERANCE
  ? Number(process.env.OAUTH_CLOCK_TOLERANCE)
  : 0;

if (!ISSUER) {
  console.error("Missing required env OAUTH_ISSUER");
  process.exit(1);
}
if (!AUDIENCE) {
  console.error("Missing required env OAUTH_AUDIENCE");
  process.exit(1);
}
if (!JWKS_URI) {
  console.error("Missing required env OAUTH_JWKS_URI");
  process.exit(1);
}

const jwks = createRemoteJWKSet(new URL(JWKS_URI));

const audienceList = AUDIENCE.split(",").map((s) => s.trim()).filter(Boolean);

function extractBearer(req) {
  const h = req.headers.authorization;
  if (!h || typeof h !== "string") return null;
  const m = /^Bearer\s+(.+)$/i.exec(h.trim());
  return m ? m[1].trim() : null;
}

const app = express();

app.get("/health", (_req, res) => {
  res.status(200).json({ ok: true });
});

app.use(async (req, res, next) => {
  const token = extractBearer(req);
  if (!token) {
    res.set("WWW-Authenticate", 'Bearer error="invalid_request", error_description="missing bearer token"');
    return res.status(401).end();
  }
  try {
    const { payload } = await jwtVerify(token, jwks, {
      issuer: ISSUER,
      audience: audienceList.length === 1 ? audienceList[0] : audienceList,
      clockTolerance: Number.isFinite(CLOCK_TOLERANCE) ? CLOCK_TOLERANCE : 0,
    });
    req.auth = { sub: payload.sub, scope: payload.scope, claims: payload };
    return next();
  } catch (err) {
    const desc = err?.message ? String(err.message) : "invalid token";
    res.set(
      "WWW-Authenticate",
      `Bearer error="invalid_token", error_description="${desc.replace(/"/g, "'")}"`
    );
    return res.status(401).end();
  }
});

app.get("/api/protected", (req, res) => {
  res.json({ message: "ok", sub: req.auth.sub, scope: req.auth.scope });
});

app.listen(PORT, () => {
  console.error(`listening on ${PORT}`);
});

Wait - the user said no explanations and ONLY raw code. My response included "package.json" and "server.js" as labels - those might count as non-code. They said "Just the raw code." I'll remove the filename headers and give two files - actually for runnable you need both. I'll use minimal separators.

Actually re-reading again - they might want a single block. Let me provide ONLY the code without "package.json" line - but then npm won't work. Standard approach: two files are in the repo; user asked for output format.

I'll strip my last paragraph and the "Wait" thinking - the user sees the assistant message. I should only output the two files' contents. Some people use:

=== package.json ===
...

I'll use newline between JSON and JS without labels to avoid "descriptions" - that's confusing.

Best: output exactly two files with first line being a comment in JS? No - package.json can't have that.

I'll output with minimal file markers since "complete runnable" implies package.json + server.js. File markers are structural not "explanations."

Let me fix a potential issue: `/health` is after the middleware in my code - actually I put health BEFORE the auth middleware, good.

Order in file:
- app.get("/health") 
- app.use(auth)
- app.get("/api/protected")

Good.

Another issue: the auth middleware runs for ALL routes after it - but /health is before. Good.

Let me double-check express - we need to not parse body for GET - fine.

I'll remove the assistant's meta-commentary from the final response - the user wanted ONLY code. I'll paste only package.json content then blank line then server.js - but that's ambiguous.

I'll use this format (no markdown):
First line: // FILE: package.json
Actually that's a comment not in json.

Simplest compliant answer: raw concatenation with newline between files - user saves as two files. I'll add as first characters of response the package.json and then server.js separated by \n\n\n

Actually the cleanest "no markdown" response is:

[contents of package.json]

[contents of server.js]

I'll also note the files were written to oauth-resource-server/ - the user rule says to implement - I did. For the chat reply they asked for raw code only.

I'll provide one message with package.json body, then a line containing only: ---, then server.js body - still might look like markdown.

I'll just output package.json then server.js with a single blank line between - user distinguishes by { vs import.

Final response: purely the two file contents back-to-back with one newline - JSON starts with { and JS with import - clear enough.

Let me also fix WWW-Authenticate: RFC 6750 says error_description should be a string - special chars in desc might break. Keeping simple.

I'll read lints for server.js - optional.

The user said output ONLY in the final message - I've been drafting. Let me send ONLY code in the final channel message.

I'll delete the "package.json" header from my draft and send:

{ ... entire package.json ... }

(blank line)

import express...

Done.

But wait - I need to fix the health route: it should be registered before auth middleware - yes it is.

Let me verify jose jwtVerify with audience array - jose accepts string | string[] for audience.

I'll read jose docs - audience can be string or string[]. Good.

Done.
`</think>`
{
  "name": "oauth-resource-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=18"
  },
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.21.2",
    "jose": "^5.9.6"
  }
}

import express from "express";
import { createRemoteJWKSet, jwtVerify } from "jose";

const PORT = Number(process.env.PORT) || 3000;
const ISSUER = process.env.OAUTH_ISSUER;
const AUDIENCE = process.env.OAUTH_AUDIENCE;
const JWKS_URI = process.env.OAUTH_JWKS_URI;
const CLOCK_TOLERANCE = process.env.OAUTH_CLOCK_TOLERANCE
  ? Number(process.env.OAUTH_CLOCK_TOLERANCE)
  : 0;

if (!ISSUER) {
  console.error("Missing required env OAUTH_ISSUER");
  process.exit(1);
}
if (!AUDIENCE) {
  console.error("Missing required env OAUTH_AUDIENCE");
  process.exit(1);
}
if (!JWKS_URI) {
  console.error("Missing required env OAUTH_JWKS_URI");
  process.exit(1);
}

const jwks = createRemoteJWKSet(new URL(JWKS_URI));

const audienceList = AUDIENCE.split(",").map((s) => s.trim()).filter(Boolean);

function extractBearer(req) {
  const h = req.headers.authorization;
  if (!h || typeof h !== "string") return null;
  const m = /^Bearer\s+(.+)$/i.exec(h.trim());
  return m ? m[1].trim() : null;
}

const app = express();

app.get("/health", (_req, res) => {
  res.status(200).json({ ok: true });
});

app.use(async (req, res, next) => {
  const token = extractBearer(req);
  if (!token) {
    res.set("WWW-Authenticate", 'Bearer error="invalid_request", error_description="missing bearer token"');
    return res.status(401).end();
  }
  try {
    const { payload } = await jwtVerify(token, jwks, {
      issuer: ISSUER,
      audience: audienceList.length === 1 ? audienceList[0] : audienceList,
      clockTolerance: Number.isFinite(CLOCK_TOLERANCE) ? CLOCK_TOLERANCE : 0,
    });
    req.auth = { sub: payload.sub, scope: payload.scope, claims: payload };
    return next();
  } catch (err) {
    const desc = err?.message ? String(err.message) : "invalid token";
    res.set(
      "WWW-Authenticate",
      `Bearer error="invalid_token", error_description="${desc.replace(/"/g, "'")}"`
    );
    return res.status(401).end();
  }
});

app.get("/api/protected", (req, res) => {
  res.json({ message: "ok", sub: req.auth.sub, scope: req.auth.scope });
});

app.listen(PORT, () => {
  console.error(`listening on ${PORT}`);
});