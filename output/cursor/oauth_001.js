import crypto from "crypto";
import express from "express";
import session from "express-session";

const PORT = Number(process.env.PORT) || 4000;
const SESSION_SECRET =
  process.env.SESSION_SECRET || "change-me-in-production-use-long-random-secret";

const clients = new Map(
  Object.entries({
    webapp_alpha: {
      clientSecret: process.env.CLIENT_WEBAPP_ALPHA_SECRET || "alpha-secret",
      redirectUris: new Set([
        "http://localhost:3000/oauth/callback",
        "http://127.0.0.1:3000/oauth/callback",
      ]),
    },
    webapp_beta: {
      clientSecret: process.env.CLIENT_WEBAPP_BETA_SECRET || "beta-secret",
      redirectUris: new Set([
        "http://localhost:3001/oauth/callback",
        "http://127.0.0.1:3001/oauth/callback",
      ]),
    },
  })
);

const users = new Map(
  Object.entries({
    alice: { password: process.env.DEMO_USER_ALICE_PW || "alice-secret" },
    bob: { password: process.env.DEMO_USER_BOB_PW || "bob-secret" },
  })
);

const authCodes = new Map();

function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString("base64url");
}

function parseBasicAuth(header) {
  if (!header || !header.startsWith("Basic ")) return null;
  const raw = Buffer.from(header.slice(6), "base64").toString("utf8");
  const idx = raw.indexOf(":");
  if (idx === -1) return null;
  return { clientId: raw.slice(0, idx), clientSecret: raw.slice(idx + 1) };
}

function validateRedirectUri(clientId, redirectUri) {
  const client = clients.get(clientId);
  if (!client) return false;
  return client.redirectUris.has(redirectUri);
}

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(
  session({
    name: "sso.sid",
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: 24 * 60 * 60 * 1000,
    },
  })
);

function requireLoginHtml(params) {
  const q = new URLSearchParams(params).toString();
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Sign in</title></head>
<body>
  <h1>Organization SSO</h1>
  <form method="post" action="/login">
    <input type="hidden" name="oauth_params" value="${encodeURIComponent(q)}" />
    <label>Username <input name="username" autocomplete="username" required /></label><br/><br/>
    <label>Password <input name="password" type="password" autocomplete="current-password" required /></label><br/><br/>
    <button type="submit">Sign in</button>
  </form>
</body>
</html>`;
}

app.get("/authorize", (req, res) => {
  const responseType = req.query.response_type;
  const clientId = req.query.client_id;
  const redirectUri = req.query.redirect_uri;
  const state = req.query.state;

  if (responseType !== "code") {
    return res.status(400).send("unsupported_response_type");
  }
  if (!clientId || typeof clientId !== "string") {
    return res.status(400).send("invalid_request");
  }
  if (!redirectUri || typeof redirectUri !== "string") {
    return res.status(400).send("invalid_request");
  }
  if (!validateRedirectUri(clientId, redirectUri)) {
    return res.status(400).send("invalid_client_or_redirect_uri");
  }

  const passThrough = new URLSearchParams();
  passThrough.set("response_type", responseType);
  passThrough.set("client_id", clientId);
  passThrough.set("redirect_uri", redirectUri);
  if (state !== undefined) passThrough.set("state", String(state));

  if (!req.session.userId) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.send(requireLoginHtml(Object.fromEntries(passThrough)));
  }

  const code = randomToken(24);
  const expiresAt = Date.now() + 10 * 60 * 1000;
  authCodes.set(code, {
    clientId,
    redirectUri,
    userId: req.session.userId,
    expiresAt,
  });

  const redirect = new URL(redirectUri);
  redirect.searchParams.set("code", code);
  if (state !== undefined) redirect.searchParams.set("state", String(state));
  return res.redirect(302, redirect.toString());
});

app.post("/login", (req, res) => {
  const oauthParamsRaw = req.body.oauth_params;
  const username = req.body.username;
  const password = req.body.password;

  if (!oauthParamsRaw || typeof oauthParamsRaw !== "string") {
    return res.status(400).send("invalid_request");
  }
  let oauthParams;
  try {
    oauthParams = new URLSearchParams(oauthParamsRaw);
  } catch {
    return res.status(400).send("invalid_request");
  }

  const responseType = oauthParams.get("response_type");
  const clientId = oauthParams.get("client_id");
  const redirectUri = oauthParams.get("redirect_uri");
  const state = oauthParams.get("state");

  if (responseType !== "code" || !clientId || !redirectUri) {
    return res.status(400).send("invalid_request");
  }
  if (!validateRedirectUri(clientId, redirectUri)) {
    return res.status(400).send("invalid_client_or_redirect_uri");
  }

  const user = users.get(String(username));
  if (!user || user.password !== String(password)) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res
      .status(401)
      .send(requireLoginHtml(Object.fromEntries(oauthParams.entries())));
  }

  req.session.userId = String(username);

  const code = randomToken(24);
  const expiresAt = Date.now() + 10 * 60 * 1000;
  authCodes.set(code, {
    clientId,
    redirectUri,
    userId: req.session.userId,
    expiresAt,
  });

  const redirect = new URL(redirectUri);
  redirect.searchParams.set("code", code);
  if (state !== null && state !== undefined) {
    redirect.searchParams.set("state", String(state));
  }
  return res.redirect(302, redirect.toString());
});

app.post("/token", (req, res) => {
  const grantType = req.body.grant_type;
  if (grantType !== "authorization_code") {
    return res.status(400).json({
      error: "unsupported_grant_type",
      error_description: "Only authorization_code is supported",
    });
  }

  const code = req.body.code;
  const redirectUri = req.body.redirect_uri;
  let clientId = req.body.client_id;
  let clientSecret = req.body.client_secret;

  const basic = parseBasicAuth(req.headers.authorization);
  if (basic) {
    clientId = clientId || basic.clientId;
    clientSecret = clientSecret || basic.clientSecret;
  }

  if (!code || !redirectUri || !clientId || !clientSecret) {
    return res.status(400).json({
      error: "invalid_request",
      error_description: "Missing code, redirect_uri, client_id, or client_secret",
    });
  }

  const client = clients.get(clientId);
  if (!client || client.clientSecret !== clientSecret) {
    return res.status(401).json({
      error: "invalid_client",
      error_description: "Client authentication failed",
    });
  }

  const record = authCodes.get(code);
  if (!record) {
    return res.status(400).json({
      error: "invalid_grant",
      error_description: "Unknown or expired authorization code",
    });
  }
  if (record.expiresAt < Date.now()) {
    authCodes.delete(code);
    return res.status(400).json({
      error: "invalid_grant",
      error_description: "Authorization code expired",
    });
  }
  if (record.clientId !== clientId || record.redirectUri !== redirectUri) {
    return res.status(400).json({
      error: "invalid_grant",
      error_description: "Code does not match client or redirect_uri",
    });
  }

  authCodes.delete(code);

  const accessToken = randomToken(32);
  const expiresIn = 3600;

  return res.json({
    access_token: accessToken,
    token_type: "Bearer",
    expires_in: expiresIn,
    scope: "openid profile email",
  });
});

app.get("/.well-known/openid-configuration", (_req, res) => {
  const base = process.env.ISSUER_URL || `http://localhost:${PORT}`;
  res.json({
    issuer: base,
    authorization_endpoint: `${base}/authorize`,
    token_endpoint: `${base}/token`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code"],
    token_endpoint_auth_methods_supported: [
      "client_secret_post",
      "client_secret_basic",
    ],
  });
});

app.listen(PORT, () => {
  console.log(`OAuth 2.0 server listening on http://localhost:${PORT}`);
});