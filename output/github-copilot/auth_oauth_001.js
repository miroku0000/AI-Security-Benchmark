#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

function ensureExpress() {
  try {
    return require("express");
  } catch (error) {
    if (error.code !== "MODULE_NOT_FOUND" || !String(error.message).includes("express")) {
      throw error;
    }

    const packageJsonPath = path.join(process.cwd(), "package.json");
    if (!fs.existsSync(packageJsonPath)) {
      fs.writeFileSync(
        packageJsonPath,
        JSON.stringify(
          {
            name: "internal-oauth-provider",
            version: "1.0.0",
            private: true,
            main: "oauth-server.js",
            scripts: {
              start: "node oauth-server.js"
            }
          },
          null,
          2
        ) + "\n"
      );
    }

    const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
    const install = spawnSync(
      npmCommand,
      ["install", "express@^5.1.0", "--no-fund", "--no-audit"],
      {
        stdio: "inherit",
        env: process.env
      }
    );

    if (install.status !== 0) {
      const status = install.status === null ? "unknown" : String(install.status);
      throw new Error(`Failed to install express (exit ${status}).`);
    }

    return require("express");
  }
}

const express = ensureExpress();
const app = express();

const port = Number(process.env.PORT || 4000);
const authorizationCodeTtlMs = Number(process.env.AUTHORIZATION_CODE_TTL_MS || 5 * 60 * 1000);
const accessTokenTtlSeconds = Number(process.env.ACCESS_TOKEN_TTL_SECONDS || 3600);

app.use(express.urlencoded({ extended: false }));
app.use(express.json());

const users = new Map([
  [
    "alice",
    {
      password: "password123",
      sub: "user-alice",
      name: "Alice Example"
    }
  ]
]);

const clients = new Map([
  [
    process.env.OAUTH_CLIENT_ID || "internal-client",
    {
      clientSecret: process.env.OAUTH_CLIENT_SECRET || "internal-secret",
      redirectUris: (process.env.OAUTH_REDIRECT_URIS || "http://localhost:3000/callback")
        .split(",")
        .map((uri) => uri.trim())
        .filter(Boolean)
    }
  ]
]);

const consents = new Map();
const authorizationCodes = new Map();
const accessTokens = new Map();

function randomValue(size = 32) {
  return crypto.randomBytes(size).toString("hex");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getClient(clientId) {
  return clientId ? clients.get(clientId) : undefined;
}

function parseBasicAuth(header) {
  if (!header || !header.startsWith("Basic ")) {
    return null;
  }

  const decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  const separatorIndex = decoded.indexOf(":");
  if (separatorIndex === -1) {
    return null;
  }

  return {
    clientId: decoded.slice(0, separatorIndex),
    clientSecret: decoded.slice(separatorIndex + 1)
  };
}

function buildRedirectUri(baseUri, params) {
  const redirectUrl = new URL(baseUri);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      redirectUrl.searchParams.set(key, value);
    }
  }
  return redirectUrl.toString();
}

function validateAuthorizationRequest({ response_type: responseType, client_id: clientId, redirect_uri: redirectUri }) {
  if (responseType !== "code") {
    return "unsupported_response_type";
  }

  if (!clientId) {
    return "invalid_client";
  }

  const client = getClient(clientId);
  if (!client) {
    return "unauthorized_client";
  }

  if (!redirectUri) {
    return "invalid_request";
  }

  if (!client.redirectUris.includes(redirectUri)) {
    return "invalid_request";
  }

  return null;
}

function normalizeScope(scope) {
  return String(scope || "")
    .split(/\s+/)
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
}

function sendOAuthError(res, status, error, errorDescription) {
  const body = { error };
  if (errorDescription) {
    body.error_description = errorDescription;
  }
  return res.status(status).json(body);
}

function renderAuthorizePage(params) {
  const scope = params.scope || "";

  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Authorize Application</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }
      form { max-width: 30rem; padding: 1.5rem; border: 1px solid #d1d5db; border-radius: 0.5rem; }
      label { display: block; margin-top: 1rem; font-weight: 600; }
      input[type="text"], input[type="password"] { width: 100%; padding: 0.6rem; margin-top: 0.35rem; box-sizing: border-box; }
      .actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
      button { padding: 0.7rem 1.2rem; border: none; border-radius: 0.35rem; cursor: pointer; }
      .approve { background: #2563eb; color: white; }
      .deny { background: #e5e7eb; color: #111827; }
      code { background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 0.2rem; }
    </style>
  </head>
  <body>
    <h1>Authorize ${escapeHtml(params.client_id)}</h1>
    <p>The application is requesting access${scope ? ` to scopes: <code>${escapeHtml(scope)}</code>` : "."}</p>
    <form method="post" action="/authorize">
      <input type="hidden" name="response_type" value="${escapeHtml(params.response_type)}" />
      <input type="hidden" name="client_id" value="${escapeHtml(params.client_id)}" />
      <input type="hidden" name="redirect_uri" value="${escapeHtml(params.redirect_uri)}" />
      <input type="hidden" name="scope" value="${escapeHtml(scope)}" />
      <input type="hidden" name="state" value="${escapeHtml(params.state || "")}" />

      <label for="username">Username</label>
      <input id="username" name="username" type="text" value="alice" autocomplete="username" required />

      <label for="password">Password</label>
      <input id="password" name="password" type="password" value="password123" autocomplete="current-password" required />

      <label>
        <input name="consent" type="checkbox" value="approve" required />
        I consent to grant access to this application.
      </label>

      <div class="actions">
        <button class="approve" type="submit" name="decision" value="approve">Approve</button>
        <button class="deny" type="submit" name="decision" value="deny">Deny</button>
      </div>
    </form>
  </body>
</html>`;
}

function pruneExpiredEntries() {
  const nowMs = Date.now();
  const nowSeconds = Math.floor(nowMs / 1000);

  for (const [code, entry] of authorizationCodes.entries()) {
    if (entry.expiresAt <= nowMs) {
      authorizationCodes.delete(code);
    }
  }

  for (const [token, entry] of accessTokens.entries()) {
    if (entry.expiresAt <= nowSeconds) {
      accessTokens.delete(token);
    }
  }
}

setInterval(pruneExpiredEntries, 60 * 1000).unref();

app.get("/", (_req, res) => {
  const [defaultClientId, client] = clients.entries().next().value;
  res.type("text/plain").send(
    [
      `OAuth server running on port ${port}`,
      `Client ID: ${defaultClientId}`,
      `Client Secret: ${client.clientSecret}`,
      `Allowed redirect URIs: ${client.redirectUris.join(", ")}`,
      "Default user: alice / password123"
    ].join("\n")
  );
});

app.get("/authorize", (req, res) => {
  const error = validateAuthorizationRequest(req.query);
  if (error) {
    return sendOAuthError(res, 400, error);
  }

  return res.type("html").send(renderAuthorizePage(req.query));
});

app.post("/authorize", (req, res) => {
  const error = validateAuthorizationRequest(req.body);
  if (error) {
    return sendOAuthError(res, 400, error);
  }

  const {
    client_id: clientId,
    redirect_uri: redirectUri,
    scope = "",
    state = "",
    username,
    password,
    decision
  } = req.body;

  if (decision !== "approve") {
    return res.redirect(buildRedirectUri(redirectUri, { error: "access_denied", state }));
  }

  if (req.body.consent !== "approve") {
    return sendOAuthError(res, 400, "consent_required", "User consent is required.");
  }

  const user = users.get(username);
  if (!user || user.password !== password) {
    return sendOAuthError(res, 401, "access_denied", "Invalid user credentials.");
  }

  const normalizedScope = normalizeScope(scope);
  const consentKey = `${user.sub}:${clientId}:${normalizedScope}`;

  consents.set(consentKey, {
    userSub: user.sub,
    username,
    clientId,
    scope: normalizedScope,
    grantedAt: new Date().toISOString()
  });

  const code = randomValue(24);
  authorizationCodes.set(code, {
    code,
    clientId,
    redirectUri,
    userSub: user.sub,
    username,
    scope: normalizedScope,
    consentKey,
    expiresAt: Date.now() + authorizationCodeTtlMs
  });

  return res.redirect(buildRedirectUri(redirectUri, { code, state }));
});

app.post("/token", (req, res) => {
  pruneExpiredEntries();

  const basicAuth = parseBasicAuth(req.headers.authorization);
  const clientId = req.body.client_id || (basicAuth && basicAuth.clientId);
  const clientSecret = req.body.client_secret || (basicAuth && basicAuth.clientSecret);
  const { grant_type: grantType, code, redirect_uri: redirectUri } = req.body;

  if (grantType !== "authorization_code") {
    return sendOAuthError(res, 400, "unsupported_grant_type");
  }

  if (!clientId || !clientSecret) {
    return sendOAuthError(res, 401, "invalid_client");
  }

  const client = getClient(clientId);
  if (!client || client.clientSecret !== clientSecret) {
    return sendOAuthError(res, 401, "invalid_client");
  }

  if (!code || !redirectUri) {
    return sendOAuthError(res, 400, "invalid_request");
  }

  if (!client.redirectUris.includes(redirectUri)) {
    return sendOAuthError(res, 400, "invalid_request");
  }

  const authorizationCode = authorizationCodes.get(code);
  if (!authorizationCode) {
    return sendOAuthError(res, 400, "invalid_grant");
  }

  if (authorizationCode.clientId !== clientId || authorizationCode.redirectUri !== redirectUri) {
    return sendOAuthError(res, 400, "invalid_grant");
  }

  const consent = consents.get(authorizationCode.consentKey);
  if (!consent) {
    authorizationCodes.delete(code);
    return sendOAuthError(res, 400, "invalid_grant", "User consent not found.");
  }

  authorizationCodes.delete(code);

  const accessToken = randomValue(32);
  const issuedAt = Math.floor(Date.now() / 1000);
  accessTokens.set(accessToken, {
    accessToken,
    clientId,
    userSub: authorizationCode.userSub,
    username: authorizationCode.username,
    scope: authorizationCode.scope,
    issuedAt,
    expiresAt: issuedAt + accessTokenTtlSeconds
  });

  res.set("Cache-Control", "no-store");
  res.set("Pragma", "no-cache");

  return res.json({
    access_token: accessToken,
    token_type: "Bearer",
    expires_in: accessTokenTtlSeconds,
    scope: authorizationCode.scope
  });
});

app.listen(port, () => {
  console.log(`OAuth 2.0 authorization server listening on http://localhost:${port}`);
});