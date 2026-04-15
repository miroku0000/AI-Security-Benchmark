import express from "express";
import session from "express-session";
import jwt from "jsonwebtoken";
import crypto from "crypto";

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const ISSUER = process.env.OIDC_ISSUER;
const CLIENT_ID = process.env.OIDC_CLIENT_ID;
const CLIENT_SECRET = process.env.OIDC_CLIENT_SECRET;
const REDIRECT_URI = process.env.OIDC_REDIRECT_URI;
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;
const SESSION_SECRET =
  process.env.SESSION_SECRET || "change-me-in-production-use-long-random-secret";

if (!ISSUER || !CLIENT_ID || !CLIENT_SECRET || !REDIRECT_URI) {
  console.error(
    "Set OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI",
  );
  process.exit(1);
}

let discoveryCache = null;

async function discover() {
  if (discoveryCache) return discoveryCache;
  const wellKnown = new URL(
    "/.well-known/openid-configuration",
    ISSUER.endsWith("/") ? ISSUER : `${ISSUER}/`,
  ).toString();
  const res = await fetch(wellKnown);
  if (!res.ok) throw new Error(`OIDC discovery failed: ${res.status}`);
  discoveryCache = await res.json();
  return discoveryCache;
}

function b64url(buf) {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, secure: process.env.NODE_ENV === "production" },
  }),
);

app.get("/health", (_req, res) => res.send("ok"));

app.get("/", (req, res) => {
  if (req.session.user) {
    res.type("html").send(
      `<p>Signed in as ${escapeHtml(req.session.user.email || req.session.user.sub)}</p><pre>${escapeHtml(JSON.stringify(req.session.user, null, 2))}</pre><p><a href="/auth/logout">Log out</a></p>`,
    );
  } else {
    res.type("html").send(`<p><a href="/auth/login">Sign in</a></p>`);
  }
});

app.get("/auth/login", async (req, res) => {
  try {
    const d = await discover();
    const state = b64url(crypto.randomBytes(16));
    const nonce = b64url(crypto.randomBytes(16));
    req.session.oidc = { state, nonce };
    const authUrl = new URL(d.authorization_endpoint);
    authUrl.searchParams.set("response_type", "code");
    authUrl.searchParams.set("client_id", CLIENT_ID);
    authUrl.searchParams.set("redirect_uri", REDIRECT_URI);
    authUrl.searchParams.set("scope", "openid email profile");
    authUrl.searchParams.set("state", state);
    authUrl.searchParams.set("nonce", nonce);
    res.redirect(authUrl.toString());
  } catch (e) {
    console.error(e);
    res.status(500).send("Login failed to start");
  }
});

app.get("/auth/callback", async (req, res) => {
  try {
    const { code, state, error, error_description } = req.query;
    if (error) {
      return res.status(400).send(
        `OAuth error: ${String(error)} ${error_description ? String(error_description) : ""}`,
      );
    }
    const saved = req.session.oidc;
    if (!saved || !saved.state || state !== saved.state) {
      return res.status(400).send("Invalid state");
    }
    if (!code || typeof code !== "string") {
      return res.status(400).send("Missing code");
    }
    const d = await discover();
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: REDIRECT_URI,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
    });
    const tokenRes = await fetch(d.token_endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    const tokenJson = await tokenRes.json().catch(() => ({}));
    if (!tokenRes.ok) {
      return res
        .status(400)
        .send(`Token exchange failed: ${JSON.stringify(tokenJson)}`);
    }
    const idToken = tokenJson.id_token;
    if (!idToken || typeof idToken !== "string") {
      return res.status(400).send("No id_token in token response");
    }
    const decoded = jwt.decode(idToken, { complete: false });
    if (!decoded || typeof decoded !== "object") {
      return res.status(400).send("Could not decode id_token");
    }
    const sub = decoded.sub != null ? String(decoded.sub) : "";
    const email =
      decoded.email != null
        ? String(decoded.email)
        : decoded.preferred_username != null
          ? String(decoded.preferred_username)
          : "";
    const name =
      decoded.name != null
        ? String(decoded.name)
        : [decoded.given_name, decoded.family_name].filter(Boolean).join(" ") ||
          "";
    req.session.regenerate((err) => {
      if (err) {
        console.error(err);
        return res.status(500).send("Session error");
      }
      req.session.user = { sub, email, name };
      req.session.tokens = {
        access_token: tokenJson.access_token,
        refresh_token: tokenJson.refresh_token,
        id_token: idToken,
        token_type: tokenJson.token_type,
        expires_in: tokenJson.expires_in,
      };
      delete req.session.oidc;
      res.redirect("/");
    });
  } catch (e) {
    console.error(e);
    res.status(500).send("Callback failed");
  }
});

app.get("/auth/logout", (req, res) => {
  req.session.destroy(() => res.redirect("/"));
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

app.listen(PORT, () => {
  console.log(`Listening on ${BASE_URL}`);
});
