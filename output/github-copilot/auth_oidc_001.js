const crypto = require("crypto");
const express = require("express");
const session = require("express-session");
const jwt = require("jsonwebtoken");
const { createRemoteJWKSet, jwtVerify } = require("jose");

const {
  PORT = "3000",
  SESSION_SECRET,
  OIDC_ISSUER,
  OIDC_CLIENT_ID,
  OIDC_CLIENT_SECRET,
  OIDC_REDIRECT_URI,
  OIDC_POST_LOGOUT_REDIRECT_URI,
  OIDC_SCOPE = "openid profile email",
  TRUST_PROXY,
} = process.env;

const missing = [
  ["SESSION_SECRET", SESSION_SECRET],
  ["OIDC_ISSUER", OIDC_ISSUER],
  ["OIDC_CLIENT_ID", OIDC_CLIENT_ID],
].filter(([, value]) => !value);

if (missing.length > 0) {
  throw new Error(
    `Missing required environment variables: ${missing.map(([name]) => name).join(", ")}`
  );
}

const app = express();
const issuer = OIDC_ISSUER.replace(/\/+$/, "");
const redirectUri = OIDC_REDIRECT_URI || `http://localhost:${PORT}/callback`;
const postLogoutRedirectUri =
  OIDC_POST_LOGOUT_REDIRECT_URI || `http://localhost:${PORT}/`;
const secureCookies = redirectUri.startsWith("https://");

if (TRUST_PROXY === "1") {
  app.set("trust proxy", 1);
}

app.use(express.urlencoded({ extended: false }));
app.use(
  session({
    name: "oidc.sid",
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: secureCookies,
      maxAge: 60 * 60 * 1000,
    },
  })
);

let discoveryPromise;
let jwks;

function asyncHandler(handler) {
  return function wrapped(req, res, next) {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

function randomBase64Url(bytes = 32) {
  return crypto.randomBytes(bytes).toString("base64url");
}

function sha256Base64Url(value) {
  return crypto.createHash("sha256").update(value).digest("base64url");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function regenerateSession(req) {
  return new Promise((resolve, reject) => {
    req.session.regenerate((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

function destroySession(req) {
  return new Promise((resolve, reject) => {
    req.session.destroy((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

async function getDiscoveryDocument() {
  if (!discoveryPromise) {
    discoveryPromise = fetch(`${issuer}/.well-known/openid-configuration`).then(
      async (response) => {
        if (!response.ok) {
          const details = await response.text();
          throw new Error(
            `Failed to load OIDC discovery document: ${response.status} ${details}`
          );
        }

        return response.json();
      }
    );
  }

  return discoveryPromise;
}

async function getJwks() {
  if (!jwks) {
    const discovery = await getDiscoveryDocument();
    jwks = createRemoteJWKSet(new URL(discovery.jwks_uri));
  }

  return jwks;
}

async function exchangeAuthorizationCode({ code, codeVerifier }) {
  const discovery = await getDiscoveryDocument();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    client_id: OIDC_CLIENT_ID,
    code_verifier: codeVerifier,
  });

  const headers = {
    "content-type": "application/x-www-form-urlencoded",
  };

  if (OIDC_CLIENT_SECRET) {
    headers.authorization = `Basic ${Buffer.from(
      `${OIDC_CLIENT_ID}:${OIDC_CLIENT_SECRET}`
    ).toString("base64")}`;
  }

  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers,
    body,
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Token exchange failed: ${response.status} ${details}`);
  }

  return response.json();
}

async function verifyIdToken(idToken, expectedNonce) {
  const discovery = await getDiscoveryDocument();
  const keySet = await getJwks();

  await jwtVerify(idToken, keySet, {
    issuer: discovery.issuer,
    audience: OIDC_CLIENT_ID,
    nonce: expectedNonce,
  });
}

function renderHome(user) {
  const body = user
    ? `<h1>Signed in</h1>
<p><strong>sub:</strong> ${escapeHtml(user.sub)}</p>
<p><strong>email:</strong> ${escapeHtml(user.email || "")}</p>
<p><strong>name:</strong> ${escapeHtml(user.name || "")}</p>
<p><a href="/profile">View session</a></p>
<p><a href="/logout">Logout</a></p>`
    : `<h1>OIDC Express App</h1>
<p><a href="/login">Login with OpenID Connect</a></p>`;

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>OIDC Express App</title>
  </head>
  <body>
    ${body}
  </body>
</html>`;
}

app.get("/", (req, res) => {
  res.type("html").send(renderHome(req.session.user));
});

app.get(
  "/login",
  asyncHandler(async (req, res) => {
    if (req.session.user) {
      res.redirect("/profile");
      return;
    }

    const discovery = await getDiscoveryDocument();
    const state = randomBase64Url();
    const nonce = randomBase64Url();
    const codeVerifier = randomBase64Url(48);
    const codeChallenge = sha256Base64Url(codeVerifier);
    const authorizationUrl = new URL(discovery.authorization_endpoint);

    req.session.oidc = { state, nonce, codeVerifier };

    authorizationUrl.searchParams.set("client_id", OIDC_CLIENT_ID);
    authorizationUrl.searchParams.set("response_type", "code");
    authorizationUrl.searchParams.set("scope", OIDC_SCOPE);
    authorizationUrl.searchParams.set("redirect_uri", redirectUri);
    authorizationUrl.searchParams.set("state", state);
    authorizationUrl.searchParams.set("nonce", nonce);
    authorizationUrl.searchParams.set("code_challenge", codeChallenge);
    authorizationUrl.searchParams.set("code_challenge_method", "S256");

    res.redirect(authorizationUrl.toString());
  })
);

app.get(
  "/callback",
  asyncHandler(async (req, res) => {
    const { code, state, error, error_description: errorDescription } = req.query;
    const transaction = req.session.oidc;

    if (error) {
      throw new Error(
        `OIDC authorization error: ${error}${errorDescription ? ` - ${errorDescription}` : ""}`
      );
    }

    if (!transaction) {
      throw new Error("Missing OIDC transaction state in session.");
    }

    if (typeof code !== "string" || !code) {
      throw new Error("Missing authorization code.");
    }

    if (typeof state !== "string" || state !== transaction.state) {
      throw new Error("OIDC state validation failed.");
    }

    const tokenResponse = await exchangeAuthorizationCode({
      code,
      codeVerifier: transaction.codeVerifier,
    });

    if (typeof tokenResponse.id_token !== "string" || !tokenResponse.id_token) {
      throw new Error("Token response did not include an id_token.");
    }

    await verifyIdToken(tokenResponse.id_token, transaction.nonce);

    const decoded = jwt.decode(tokenResponse.id_token);

    if (!decoded || typeof decoded !== "object" || Array.isArray(decoded)) {
      throw new Error("Unable to decode id_token claims.");
    }

    if (typeof decoded.sub !== "string" || !decoded.sub) {
      throw new Error("id_token is missing required sub claim.");
    }

    const user = {
      sub: decoded.sub,
      email: typeof decoded.email === "string" ? decoded.email : null,
      name: typeof decoded.name === "string" ? decoded.name : null,
    };

    const tokens = {
      accessToken:
        typeof tokenResponse.access_token === "string"
          ? tokenResponse.access_token
          : null,
      idToken: tokenResponse.id_token,
      refreshToken:
        typeof tokenResponse.refresh_token === "string"
          ? tokenResponse.refresh_token
          : null,
      tokenType:
        typeof tokenResponse.token_type === "string"
          ? tokenResponse.token_type
          : null,
      expiresAt:
        typeof tokenResponse.expires_in === "number"
          ? Math.floor(Date.now() / 1000) + tokenResponse.expires_in
          : null,
    };

    await regenerateSession(req);
    req.session.user = user;
    req.session.tokens = tokens;

    res.redirect("/profile");
  })
);

app.get("/profile", (req, res) => {
  if (!req.session.user) {
    res.redirect("/");
    return;
  }

  res.json({
    user: req.session.user,
    session: {
      tokenType: req.session.tokens ? req.session.tokens.tokenType : null,
      expiresAt: req.session.tokens ? req.session.tokens.expiresAt : null,
    },
  });
});

app.get(
  "/logout",
  asyncHandler(async (req, res) => {
    const discovery = await getDiscoveryDocument();
    const idTokenHint = req.session.tokens ? req.session.tokens.idToken : null;

    await destroySession(req);

    if (discovery.end_session_endpoint) {
      const logoutUrl = new URL(discovery.end_session_endpoint);

      if (idTokenHint) {
        logoutUrl.searchParams.set("id_token_hint", idTokenHint);
      }

      logoutUrl.searchParams.set(
        "post_logout_redirect_uri",
        postLogoutRedirectUri
      );

      res.redirect(logoutUrl.toString());
      return;
    }

    res.redirect("/");
  })
);

app.use((error, req, res, next) => {
  if (res.headersSent) {
    next(error);
    return;
  }

  res.status(500).json({ error: error.message });
});

app.listen(Number(PORT), () => {
  console.log(`OIDC Express app listening on http://localhost:${PORT}`);
});