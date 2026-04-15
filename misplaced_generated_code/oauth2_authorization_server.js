#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const express = require('express');

const app = express();

app.disable('x-powered-by');
app.use(express.urlencoded({ extended: false }));
app.use(express.json({ limit: '1mb' }));

const PORT = parseInt(process.env.PORT || '3000', 10);
const ISSUER = process.env.OAUTH_ISSUER || `http://localhost:${PORT}`;

const AUTH_CODE_TTL_MS = parseInt(process.env.OAUTH_AUTH_CODE_TTL_MS || '300000', 10); // 5 minutes
const ACCESS_TOKEN_TTL_MS = parseInt(process.env.OAUTH_ACCESS_TOKEN_TTL_MS || '3600000', 10); // 1 hour

function nowMs() {
  return Date.now();
}

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function randomId(bytes = 32) {
  return b64url(crypto.randomBytes(bytes));
}

function timingSafeEqualStr(a, b) {
  const ab = Buffer.from(String(a || ''), 'utf8');
  const bb = Buffer.from(String(b || ''), 'utf8');
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

function normalizeRedirectUri(uri) {
  try {
    const u = new URL(uri);
    if (!['http:', 'https:'].includes(u.protocol)) return null;
    u.hash = '';
    return u.toString();
  } catch {
    return null;
  }
}

function jsonError(res, status, error, desc) {
  const body = { error };
  if (desc) body.error_description = desc;
  res.status(status).type('application/json').send(JSON.stringify(body));
}

function parseBasicAuth(header) {
  if (!header) return null;
  const m = String(header).match(/^Basic\s+(.+)$/i);
  if (!m) return null;
  let decoded;
  try {
    decoded = Buffer.from(m[1], 'base64').toString('utf8');
  } catch {
    return null;
  }
  const idx = decoded.indexOf(':');
  if (idx < 0) return null;
  return {
    username: decoded.slice(0, idx),
    password: decoded.slice(idx + 1),
  };
}

// In-memory client registry (MVP).
// For production, store in DB and manage secrets securely.
const clients = new Map([
  [
    'webapp-1',
    {
      client_id: 'webapp-1',
      client_secret: process.env.OAUTH_CLIENT_SECRET_WEBAPP_1 || 'dev-secret-change-me',
      redirect_uris: new Set([
        normalizeRedirectUri(process.env.OAUTH_REDIRECT_URI_WEBAPP_1 || 'http://localhost:8080/callback'),
      ].filter(Boolean)),
      allow_scopes: new Set(['openid', 'profile', 'email']),
    },
  ],
]);

// Auth codes: code -> { client_id, redirect_uri, scope, expires_at, used, user }
const authCodes = new Map();
// Tokens: token -> { client_id, scope, expires_at, user }
const accessTokens = new Map();

function getClient(clientId) {
  return clients.get(clientId) || null;
}

function validateRedirectUri(client, redirectUri) {
  const norm = normalizeRedirectUri(redirectUri);
  if (!norm) return { ok: false, normalized: null };
  if (!client.redirect_uris.has(norm)) return { ok: false, normalized: norm };
  return { ok: true, normalized: norm };
}

function parseScope(scopeStr) {
  if (!scopeStr) return [];
  return String(scopeStr)
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function sanitizeScope(client, requestedScopes) {
  if (!requestedScopes.length) return '';
  const allowed = [];
  for (const s of requestedScopes) {
    if (client.allow_scopes.has(s)) allowed.push(s);
  }
  return allowed.join(' ');
}

function cleanupExpired() {
  const t = nowMs();
  for (const [code, rec] of authCodes.entries()) {
    if (rec.expires_at <= t || rec.used) authCodes.delete(code);
  }
  for (const [tok, rec] of accessTokens.entries()) {
    if (rec.expires_at <= t) accessTokens.delete(tok);
  }
}

setInterval(cleanupExpired, 60_000).unref();

app.get('/.well-known/openid-configuration', (req, res) => {
  // Minimal discovery doc (useful for internal integration), even though we’re not implementing full OIDC.
  res.type('application/json').send(
    JSON.stringify({
      issuer: ISSUER,
      authorization_endpoint: `${ISSUER}/authorize`,
      token_endpoint: `${ISSUER}/token`,
      response_types_supported: ['code'],
      grant_types_supported: ['authorization_code'],
      token_endpoint_auth_methods_supported: ['client_secret_basic', 'client_secret_post'],
    })
  );
});

app.get('/health', (req, res) => {
  res.type('application/json').send(JSON.stringify({ ok: true }));
});

// Authorization endpoint (no login UI in MVP).
// Simulates an authenticated user via header or query parameter for internal testing.
app.get('/authorize', (req, res) => {
  const responseType = String(req.query.response_type || 'code');
  if (responseType !== 'code') {
    return jsonError(res, 400, 'unsupported_response_type', 'Only response_type=code is supported');
  }

  const clientId = String(req.query.client_id || '');
  const redirectUriRaw = String(req.query.redirect_uri || '');
  const state = req.query.state !== undefined ? String(req.query.state) : undefined;
  const scopeRequested = parseScope(req.query.scope);

  if (!clientId) return jsonError(res, 400, 'invalid_request', 'Missing client_id');
  if (!redirectUriRaw) return jsonError(res, 400, 'invalid_request', 'Missing redirect_uri');

  const client = getClient(clientId);
  if (!client) return jsonError(res, 400, 'unauthorized_client', 'Unknown client_id');

  const redirectCheck = validateRedirectUri(client, redirectUriRaw);
  if (!redirectCheck.ok) return jsonError(res, 400, 'invalid_request', 'Invalid redirect_uri');

  const scope = sanitizeScope(client, scopeRequested);

  // MVP "user" identity (replace with real SSO session).
  const user =
    (req.header('x-internal-user') && String(req.header('x-internal-user')).trim()) ||
    (req.query.user && String(req.query.user).trim()) ||
    'internal-user';

  const code = randomId(24);
  const expiresAt = nowMs() + AUTH_CODE_TTL_MS;
  authCodes.set(code, {
    client_id: clientId,
    redirect_uri: redirectCheck.normalized,
    scope,
    expires_at: expiresAt,
    used: false,
    user,
  });

  const redirectUrl = new URL(redirectCheck.normalized);
  redirectUrl.searchParams.set('code', code);
  if (state !== undefined) redirectUrl.searchParams.set('state', state);

  res.redirect(302, redirectUrl.toString());
});

app.post('/token', (req, res) => {
  const grantType = String(req.body.grant_type || '');
  if (grantType !== 'authorization_code') {
    return jsonError(res, 400, 'unsupported_grant_type', 'Only grant_type=authorization_code is supported');
  }

  const code = String(req.body.code || '');
  const redirectUriRaw = String(req.body.redirect_uri || '');

  const basic = parseBasicAuth(req.header('authorization'));
  const clientId = basic?.username ? String(basic.username) : String(req.body.client_id || '');
  const clientSecret = basic?.password ? String(basic.password) : String(req.body.client_secret || '');

  if (!clientId) return jsonError(res, 401, 'invalid_client', 'Missing client authentication');
  if (!clientSecret) return jsonError(res, 401, 'invalid_client', 'Missing client authentication');
  if (!code) return jsonError(res, 400, 'invalid_request', 'Missing code');
  if (!redirectUriRaw) return jsonError(res, 400, 'invalid_request', 'Missing redirect_uri');

  const client = getClient(clientId);
  if (!client) return jsonError(res, 401, 'invalid_client', 'Invalid client');
  if (!timingSafeEqualStr(client.client_secret, clientSecret)) {
    return jsonError(res, 401, 'invalid_client', 'Invalid client');
  }

  const redirectCheck = validateRedirectUri(client, redirectUriRaw);
  if (!redirectCheck.ok) return jsonError(res, 400, 'invalid_grant', 'redirect_uri mismatch');

  const rec = authCodes.get(code);
  if (!rec) return jsonError(res, 400, 'invalid_grant', 'Invalid code');
  if (rec.used) return jsonError(res, 400, 'invalid_grant', 'Code already used');
  if (rec.expires_at <= nowMs()) {
    authCodes.delete(code);
    return jsonError(res, 400, 'invalid_grant', 'Code expired');
  }
  if (rec.client_id !== clientId) return jsonError(res, 400, 'invalid_grant', 'Invalid code');
  if (rec.redirect_uri !== redirectCheck.normalized) return jsonError(res, 400, 'invalid_grant', 'redirect_uri mismatch');

  rec.used = true;
  authCodes.set(code, rec);

  const token = randomId(32);
  const expiresAt = nowMs() + ACCESS_TOKEN_TTL_MS;
  accessTokens.set(token, {
    client_id: clientId,
    scope: rec.scope,
    expires_at: expiresAt,
    user: rec.user,
  });

  res
    .status(200)
    .type('application/json')
    .send(
      JSON.stringify({
        access_token: token,
        token_type: 'Bearer',
        expires_in: Math.max(1, Math.floor(ACCESS_TOKEN_TTL_MS / 1000)),
        scope: rec.scope || undefined,
      })
    );
});

app.get('/introspect', (req, res) => {
  // Optional helper for internal debugging.
  const auth = String(req.header('authorization') || '');
  const m = auth.match(/^Bearer\s+(.+)$/i);
  const token = m ? m[1] : String(req.query.token || '');
  if (!token) return jsonError(res, 400, 'invalid_request', 'Missing token');
  const rec = accessTokens.get(token);
  const active = !!rec && rec.expires_at > nowMs();
  res.type('application/json').send(
    JSON.stringify(
      active
        ? {
            active: true,
            client_id: rec.client_id,
            scope: rec.scope,
            exp: Math.floor(rec.expires_at / 1000),
            sub: rec.user,
            iss: ISSUER,
          }
        : { active: false }
    )
  );
});

app.listen(PORT, () => {
  // Intentionally no console noise beyond a single line for local dev.
  // eslint-disable-next-line no-console
  console.log(`OAuth2 authorization server listening on ${ISSUER}`);
});

