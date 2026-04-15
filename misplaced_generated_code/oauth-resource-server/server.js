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
