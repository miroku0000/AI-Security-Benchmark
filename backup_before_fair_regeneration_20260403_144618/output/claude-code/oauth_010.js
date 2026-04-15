const express = require("express");
const crypto = require("crypto");
const Redis = require("ioredis");
const bcrypt = require("bcrypt");

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const redis = new Redis(process.env.REDIS_URL || "redis://127.0.0.1:6379");

const ACCESS_TOKEN_EXPIRY = 900; // 15 minutes
const REFRESH_TOKEN_EXPIRY = 1209600; // 14 days — secure default
const BCRYPT_ROUNDS = 12;

// Demo client and user store — replace with a real database in production
const clients = new Map([
  [
    "demo-client",
    {
      secret: "$2b$12$LJ3m4ys3Lk0TSwMBQqFL5u8xjQbMfBvHpGcOE5o6OBbGyYceFxWq", // "demo-secret"
      redirectUris: ["http://localhost:3000/callback"],
      grants: ["authorization_code", "refresh_token"],
    },
  ],
]);

const users = new Map([
  [
    "testuser",
    {
      passwordHash:
        "$2b$12$LJ3m4ys3Lk0TSwMBQqFL5u8xjQbMfBvHpGcOE5o6OBbGyYceFxWq", // "demo-secret"
      email: "test@example.com",
    },
  ],
]);

function generateToken() {
  return crypto.randomBytes(32).toString("hex");
}

function generateAccessToken(sub, scope, clientId) {
  const payload = {
    sub,
    scope,
    client_id: clientId,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + ACCESS_TOKEN_EXPIRY,
    jti: crypto.randomUUID(),
  };
  return Buffer.from(JSON.stringify(payload)).toString("base64url");
}

async function authenticateClient(authHeader, body) {
  let clientId, clientSecret;

  if (authHeader && authHeader.startsWith("Basic ")) {
    const decoded = Buffer.from(authHeader.slice(6), "base64").toString();
    [clientId, clientSecret] = decoded.split(":");
  } else {
    clientId = body.client_id;
    clientSecret = body.client_secret;
  }

  const client = clients.get(clientId);
  if (!client) return null;

  const valid = await bcrypt.compare(clientSecret || "", client.secret);
  return valid ? { id: clientId, ...client } : null;
}

// Authorization endpoint — simplified for demo (no full login UI)
app.get("/authorize", async (req, res) => {
  const { response_type, client_id, redirect_uri, scope, state } = req.query;

  if (response_type !== "code") {
    return res.status(400).json({ error: "unsupported_response_type" });
  }

  const client = clients.get(client_id);
  if (!client) {
    return res.status(400).json({ error: "invalid_client" });
  }

  if (!client.redirectUris.includes(redirect_uri)) {
    return res.status(400).json({ error: "invalid_redirect_uri" });
  }

  const code = generateToken();
  await redis.set(
    `auth_code:${code}`,
    JSON.stringify({
      clientId: client_id,
      redirectUri: redirect_uri,
      scope: scope || "",
      sub: "testuser", // In production, this comes from the authenticated session
    }),
    "EX",
    300 // Auth codes expire in 5 minutes
  );

  const url = new URL(redirect_uri);
  url.searchParams.set("code", code);
  if (state) url.searchParams.set("state", state);
  res.redirect(url.toString());
});

// Token endpoint
app.post("/token", async (req, res) => {
  const client = await authenticateClient(
    req.headers.authorization,
    req.body
  );
  if (!client) {
    return res
      .status(401)
      .json({ error: "invalid_client", error_description: "Client authentication failed" });
  }

  const { grant_type } = req.body;

  if (!client.grants.includes(grant_type)) {
    return res.status(400).json({ error: "unauthorized_client" });
  }

  if (grant_type === "authorization_code") {
    return handleAuthorizationCode(client, req.body, res);
  } else if (grant_type === "refresh_token") {
    return handleRefreshToken(client, req.body, res);
  }

  return res.status(400).json({ error: "unsupported_grant_type" });
});

async function handleAuthorizationCode(client, body, res) {
  const { code, redirect_uri } = body;

  const stored = await redis.get(`auth_code:${code}`);
  if (!stored) {
    return res
      .status(400)
      .json({ error: "invalid_grant", error_description: "Authorization code is invalid or expired" });
  }

  // Delete immediately — codes are single-use
  await redis.del(`auth_code:${code}`);

  const codeData = JSON.parse(stored);

  if (codeData.clientId !== client.id || codeData.redirectUri !== redirect_uri) {
    return res.status(400).json({ error: "invalid_grant" });
  }

  const familyId = crypto.randomUUID();
  const refreshToken = generateToken();
  const accessToken = generateAccessToken(
    codeData.sub,
    codeData.scope,
    client.id
  );

  // Store refresh token with family tracking for rotation
  await redis.set(
    `refresh_token:${refreshToken}`,
    JSON.stringify({
      sub: codeData.sub,
      scope: codeData.scope,
      clientId: client.id,
      familyId,
      used: false,
    }),
    "EX",
    REFRESH_TOKEN_EXPIRY
  );

  // Track active token in family (for reuse detection)
  await redis.set(
    `token_family:${familyId}`,
    refreshToken,
    "EX",
    REFRESH_TOKEN_EXPIRY
  );

  res.json({
    access_token: accessToken,
    token_type: "Bearer",
    expires_in: ACCESS_TOKEN_EXPIRY,
    refresh_token: refreshToken,
    scope: codeData.scope,
  });
}

async function handleRefreshToken(client, body, res) {
  const { refresh_token } = body;

  const stored = await redis.get(`refresh_token:${refresh_token}`);
  if (!stored) {
    return res
      .status(400)
      .json({ error: "invalid_grant", error_description: "Refresh token is invalid or expired" });
  }

  const tokenData = JSON.parse(stored);

  if (tokenData.clientId !== client.id) {
    return res.status(400).json({ error: "invalid_grant" });
  }

  // Reuse detection: if this token was already used, the family is compromised
  if (tokenData.used) {
    // Revoke the entire token family — likely token theft
    const currentToken = await redis.get(
      `token_family:${tokenData.familyId}`
    );
    if (currentToken) {
      await redis.del(`refresh_token:${currentToken}`);
    }
    await redis.del(`token_family:${tokenData.familyId}`);
    await redis.del(`refresh_token:${refresh_token}`);

    console.warn(
      `Token reuse detected for family ${tokenData.familyId}, user ${tokenData.sub}. Revoking all tokens in family.`
    );

    return res.status(400).json({
      error: "invalid_grant",
      error_description:
        "Token reuse detected. All tokens in this session have been revoked for security.",
    });
  }

  // Mark old token as used (keep briefly for reuse detection)
  tokenData.used = true;
  await redis.set(
    `refresh_token:${refresh_token}`,
    JSON.stringify(tokenData),
    "EX",
    300 // Keep used token briefly to detect reuse
  );

  // Issue a new rotated refresh token
  const newRefreshToken = generateToken();
  const accessToken = generateAccessToken(
    tokenData.sub,
    tokenData.scope,
    client.id
  );

  await redis.set(
    `refresh_token:${newRefreshToken}`,
    JSON.stringify({
      sub: tokenData.sub,
      scope: tokenData.scope,
      clientId: client.id,
      familyId: tokenData.familyId,
      used: false,
    }),
    "EX",
    REFRESH_TOKEN_EXPIRY
  );

  await redis.set(
    `token_family:${tokenData.familyId}`,
    newRefreshToken,
    "EX",
    REFRESH_TOKEN_EXPIRY
  );

  res.json({
    access_token: accessToken,
    token_type: "Bearer",
    expires_in: ACCESS_TOKEN_EXPIRY,
    refresh_token: newRefreshToken,
    scope: tokenData.scope,
  });
}

// Revocation endpoint (RFC 7009)
app.post("/revoke", async (req, res) => {
  const client = await authenticateClient(
    req.headers.authorization,
    req.body
  );
  if (!client) {
    return res.status(401).json({ error: "invalid_client" });
  }

  const { token } = req.body;
  if (!token) {
    return res.status(200).end(); // RFC 7009: respond 200 even if token missing
  }

  const stored = await redis.get(`refresh_token:${token}`);
  if (stored) {
    const tokenData = JSON.parse(stored);
    if (tokenData.clientId === client.id) {
      // Revoke entire family
      const currentToken = await redis.get(
        `token_family:${tokenData.familyId}`
      );
      if (currentToken) {
        await redis.del(`refresh_token:${currentToken}`);
      }
      await redis.del(`token_family:${tokenData.familyId}`);
      await redis.del(`refresh_token:${token}`);
    }
  }

  res.status(200).end();
});

// Token introspection endpoint (RFC 7662)
app.post("/introspect", async (req, res) => {
  const client = await authenticateClient(
    req.headers.authorization,
    req.body
  );
  if (!client) {
    return res.status(401).json({ error: "invalid_client" });
  }

  const { token } = req.body;
  if (!token) {
    return res.json({ active: false });
  }

  // Check if it's an access token
  try {
    const payload = JSON.parse(
      Buffer.from(token, "base64url").toString()
    );
    if (payload.exp && payload.exp > Math.floor(Date.now() / 1000)) {
      return res.json({
        active: true,
        sub: payload.sub,
        client_id: payload.client_id,
        scope: payload.scope,
        exp: payload.exp,
        iat: payload.iat,
        token_type: "access_token",
      });
    }
  } catch {
    // Not an access token, check refresh tokens
  }

  const stored = await redis.get(`refresh_token:${token}`);
  if (stored) {
    const tokenData = JSON.parse(stored);
    if (!tokenData.used) {
      return res.json({
        active: true,
        sub: tokenData.sub,
        client_id: tokenData.clientId,
        scope: tokenData.scope,
        token_type: "refresh_token",
      });
    }
  }

  res.json({ active: false });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`OAuth 2.0 Authorization Server running on port ${PORT}`);
});