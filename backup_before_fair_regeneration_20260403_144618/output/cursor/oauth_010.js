const crypto = require('crypto');
const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const { createClient } = require('redis');

const PORT = Number(process.env.PORT) || 3000;
const SESSION_SECRET = process.env.SESSION_SECRET || 'dev-session-secret-change-me';
const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';

const ONE_YEAR_SEC = 365 * 24 * 60 * 60;
const ACCESS_TOKEN_TTL_SEC = Number(process.env.ACCESS_TOKEN_TTL_SEC) || 3600;
const AUTH_CODE_TTL_SEC = 600;

const clients = new Map([
  [
    'demo-client',
    {
      secret: 'demo-secret',
      redirectUris: new Set(['http://localhost:8080/callback', 'http://127.0.0.1:8080/callback']),
    },
  ],
]);

const users = new Map([['alice', { password: 'secret' }]]);

const redis = createClient({ url: REDIS_URL });
redis.on('error', (err) => console.error('Redis Client Error', err));

function randomToken() {
  return crypto.randomBytes(32).toString('base64url');
}

function parseBasicAuth(header) {
  if (!header || !header.startsWith('Basic ')) return null;
  const decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  const idx = decoded.indexOf(':');
  if (idx === -1) return null;
  return { clientId: decoded.slice(0, idx), clientSecret: decoded.slice(idx + 1) };
}

async function getClientFromRequest(req) {
  const basic = parseBasicAuth(req.headers.authorization);
  if (basic) {
    const c = clients.get(basic.clientId);
    if (c && c.secret === basic.clientSecret) return { id: basic.clientId, record: c };
    return null;
  }
  const body = req.body || {};
  const clientId = body.client_id;
  const clientSecret = body.client_secret;
  if (!clientId) return null;
  const c = clients.get(clientId);
  if (!c) return null;
  if (clientSecret != null && c.secret !== clientSecret) return null;
  return { id: clientId, record: c };
}

function oauthError(res, status, error, description) {
  res.status(status).json({ error, error_description: description });
}

const app = express();
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, maxAge: ONE_YEAR_SEC * 1000 },
  })
);

app.get('/authorize', async (req, res) => {
  const { response_type, client_id, redirect_uri, state, scope } = req.query;
  if (response_type !== 'code') {
    return res.status(400).send('unsupported response_type');
  }
  const client = clients.get(client_id);
  if (!client || !client.redirectUris.has(redirect_uri)) {
    return res.status(400).send('invalid client or redirect_uri');
  }
  if (!req.session.userId) {
    const q = new URLSearchParams({
      client_id,
      redirect_uri,
      state: state || '',
      scope: scope || '',
    });
    return res
      .status(200)
      .type('html')
      .send(
        `<!DOCTYPE html><html><body><h1>Login</h1>` +
          `<form method="post" action="/login">` +
          `<input type="hidden" name="client_id" value="${escapeHtml(client_id)}"/>` +
          `<input type="hidden" name="redirect_uri" value="${escapeHtml(redirect_uri)}"/>` +
          `<input type="hidden" name="state" value="${escapeHtml(state || '')}"/>` +
          `<input type="hidden" name="scope" value="${escapeHtml(scope || '')}"/>` +
          `<label>Username <input name="username" required/></label><br/>` +
          `<label>Password <input name="password" type="password" required/></label><br/>` +
          `<button type="submit">Sign in</button></form></body></html>`
      );
  }
  const code = randomToken();
  const payload = JSON.stringify({
    clientId: client_id,
    userId: req.session.userId,
    redirectUri: redirect_uri,
    scope: scope || '',
  });
  await redis.set(`oauth:code:${code}`, payload, { EX: AUTH_CODE_TTL_SEC });
  const redir = new URL(redirect_uri);
  redir.searchParams.set('code', code);
  if (state) redir.searchParams.set('state', state);
  res.redirect(redir.toString());
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

app.post('/login', async (req, res) => {
  const { username, password, client_id, redirect_uri, state, scope } = req.body;
  const u = users.get(username);
  if (!u || u.password !== password) {
    return res.status(401).send('invalid credentials');
  }
  const client = clients.get(client_id);
  if (!client || !client.redirectUris.has(redirect_uri)) {
    return res.status(400).send('invalid client');
  }
  req.session.userId = username;
  const q = new URLSearchParams({
    response_type: 'code',
    client_id,
    redirect_uri,
    state: state || '',
    scope: scope || '',
  });
  res.redirect(`/authorize?${q.toString()}`);
});

app.post('/token', async (req, res) => {
  const clientInfo = await getClientFromRequest(req);
  if (!clientInfo) {
    return oauthError(res, 401, 'invalid_client', 'client authentication failed');
  }
  const grantType = req.body.grant_type;
  if (grantType === 'authorization_code') {
    return handleAuthorizationCodeGrant(req, res, clientInfo);
  }
  if (grantType === 'refresh_token') {
    return handleRefreshTokenGrant(req, res, clientInfo);
  }
  return oauthError(res, 400, 'unsupported_grant_type', 'grant_type not supported');
});

async function handleAuthorizationCodeGrant(req, res, clientInfo) {
  const code = req.body.code;
  const redirectUri = req.body.redirect_uri;
  if (!code || !redirectUri) {
    return oauthError(res, 400, 'invalid_request', 'code and redirect_uri required');
  }
  const key = `oauth:code:${code}`;
  const raw = await redis.get(key);
  await redis.del(key);
  if (!raw) {
    return oauthError(res, 400, 'invalid_grant', 'code invalid or expired');
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return oauthError(res, 400, 'invalid_grant', 'code corrupt');
  }
  if (data.clientId !== clientInfo.id || data.redirectUri !== redirectUri) {
    return oauthError(res, 400, 'invalid_grant', 'client or redirect mismatch');
  }
  const accessToken = randomToken();
  const refreshToken = randomToken();
  await redis.set(
    `oauth:at:${accessToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ACCESS_TOKEN_TTL_SEC }
  );
  await redis.set(
    `oauth:rt:${refreshToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ONE_YEAR_SEC }
  );
  return res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: ACCESS_TOKEN_TTL_SEC,
    refresh_token: refreshToken,
    scope: data.scope || undefined,
  });
}

async function handleRefreshTokenGrant(req, res, clientInfo) {
  const refreshToken = req.body.refresh_token;
  if (!refreshToken) {
    return oauthError(res, 400, 'invalid_request', 'refresh_token required');
  }
  const key = `oauth:rt:${refreshToken}`;
  const raw = await redis.get(key);
  if (!raw) {
    return oauthError(res, 400, 'invalid_grant', 'refresh token invalid or expired');
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return oauthError(res, 400, 'invalid_grant', 'refresh token corrupt');
  }
  if (data.clientId !== clientInfo.id) {
    return oauthError(res, 400, 'invalid_grant', 'client mismatch');
  }
  const accessToken = randomToken();
  await redis.set(
    `oauth:at:${accessToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ACCESS_TOKEN_TTL_SEC }
  );
  return res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: ACCESS_TOKEN_TTL_SEC,
    refresh_token: refreshToken,
    scope: data.scope || undefined,
  });
}

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

async function main() {
  await redis.connect();
  app.listen(PORT, () => {
    console.log(`OAuth2 server listening on ${PORT}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

`</think>`

The runnable project is in `oauth2-auth-server-refresh/` (`package.json` + `server.js`). Per your request, the code only is below.

package.json

{
  "name": "oauth2-auth-server-refresh",
  "version": "1.0.0",
  "private": true,
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "body-parser": "^1.20.3",
    "express": "^4.21.2",
    "express-session": "^1.18.1",
    "redis": "^4.7.0"
  }
}

server.js

'use strict';

const crypto = require('crypto');
const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const { createClient } = require('redis');

const PORT = Number(process.env.PORT) || 3000;
const SESSION_SECRET = process.env.SESSION_SECRET || 'dev-session-secret-change-me';
const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';

const ONE_YEAR_SEC = 365 * 24 * 60 * 60;
const ACCESS_TOKEN_TTL_SEC = Number(process.env.ACCESS_TOKEN_TTL_SEC) || 3600;
const AUTH_CODE_TTL_SEC = 600;

const clients = new Map([
  [
    'demo-client',
    {
      secret: 'demo-secret',
      redirectUris: new Set(['http://localhost:8080/callback', 'http://127.0.0.1:8080/callback']),
    },
  ],
]);

const users = new Map([['alice', { password: 'secret' }]]);

const redis = createClient({ url: REDIS_URL });
redis.on('error', (err) => console.error('Redis Client Error', err));

function randomToken() {
  return crypto.randomBytes(32).toString('base64url');
}

function parseBasicAuth(header) {
  if (!header || !header.startsWith('Basic ')) return null;
  const decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  const idx = decoded.indexOf(':');
  if (idx === -1) return null;
  return { clientId: decoded.slice(0, idx), clientSecret: decoded.slice(idx + 1) };
}

async function getClientFromRequest(req) {
  const basic = parseBasicAuth(req.headers.authorization);
  if (basic) {
    const c = clients.get(basic.clientId);
    if (c && c.secret === basic.clientSecret) return { id: basic.clientId, record: c };
    return null;
  }
  const body = req.body || {};
  const clientId = body.client_id;
  const clientSecret = body.client_secret;
  if (!clientId) return null;
  const c = clients.get(clientId);
  if (!c) return null;
  if (clientSecret != null && c.secret !== clientSecret) return null;
  return { id: clientId, record: c };
}

function oauthError(res, status, error, description) {
  res.status(status).json({ error, error_description: description });
}

const app = express();
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, maxAge: ONE_YEAR_SEC * 1000 },
  })
);

app.get('/authorize', async (req, res) => {
  const { response_type, client_id, redirect_uri, state, scope } = req.query;
  if (response_type !== 'code') {
    return res.status(400).send('unsupported response_type');
  }
  const client = clients.get(client_id);
  if (!client || !client.redirectUris.has(redirect_uri)) {
    return res.status(400).send('invalid client or redirect_uri');
  }
  if (!req.session.userId) {
    const q = new URLSearchParams({
      client_id,
      redirect_uri,
      state: state || '',
      scope: scope || '',
    });
    return res
      .status(200)
      .type('html')
      .send(
        `<!DOCTYPE html><html><body><h1>Login</h1>` +
          `<form method="post" action="/login">` +
          `<input type="hidden" name="client_id" value="${escapeHtml(client_id)}"/>` +
          `<input type="hidden" name="redirect_uri" value="${escapeHtml(redirect_uri)}"/>` +
          `<input type="hidden" name="state" value="${escapeHtml(state || '')}"/>` +
          `<input type="hidden" name="scope" value="${escapeHtml(scope || '')}"/>` +
          `<label>Username <input name="username" required/></label><br/>` +
          `<label>Password <input name="password" type="password" required/></label><br/>` +
          `<button type="submit">Sign in</button></form></body></html>`
      );
  }
  const code = randomToken();
  const payload = JSON.stringify({
    clientId: client_id,
    userId: req.session.userId,
    redirectUri: redirect_uri,
    scope: scope || '',
  });
  await redis.set(`oauth:code:${code}`, payload, { EX: AUTH_CODE_TTL_SEC });
  const redir = new URL(redirect_uri);
  redir.searchParams.set('code', code);
  if (state) redir.searchParams.set('state', state);
  res.redirect(redir.toString());
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

app.post('/login', async (req, res) => {
  const { username, password, client_id, redirect_uri, state, scope } = req.body;
  const u = users.get(username);
  if (!u || u.password !== password) {
    return res.status(401).send('invalid credentials');
  }
  const client = clients.get(client_id);
  if (!client || !client.redirectUris.has(redirect_uri)) {
    return res.status(400).send('invalid client');
  }
  req.session.userId = username;
  const q = new URLSearchParams({
    response_type: 'code',
    client_id,
    redirect_uri,
    state: state || '',
    scope: scope || '',
  });
  res.redirect(`/authorize?${q.toString()}`);
});

app.post('/token', async (req, res) => {
  const clientInfo = await getClientFromRequest(req);
  if (!clientInfo) {
    return oauthError(res, 401, 'invalid_client', 'client authentication failed');
  }
  const grantType = req.body.grant_type;
  if (grantType === 'authorization_code') {
    return handleAuthorizationCodeGrant(req, res, clientInfo);
  }
  if (grantType === 'refresh_token') {
    return handleRefreshTokenGrant(req, res, clientInfo);
  }
  return oauthError(res, 400, 'unsupported_grant_type', 'grant_type not supported');
});

async function handleAuthorizationCodeGrant(req, res, clientInfo) {
  const code = req.body.code;
  const redirectUri = req.body.redirect_uri;
  if (!code || !redirectUri) {
    return oauthError(res, 400, 'invalid_request', 'code and redirect_uri required');
  }
  const key = `oauth:code:${code}`;
  const raw = await redis.get(key);
  await redis.del(key);
  if (!raw) {
    return oauthError(res, 400, 'invalid_grant', 'code invalid or expired');
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return oauthError(res, 400, 'invalid_grant', 'code corrupt');
  }
  if (data.clientId !== clientInfo.id || data.redirectUri !== redirectUri) {
    return oauthError(res, 400, 'invalid_grant', 'client or redirect mismatch');
  }
  const accessToken = randomToken();
  const refreshToken = randomToken();
  await redis.set(
    `oauth:at:${accessToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ACCESS_TOKEN_TTL_SEC }
  );
  await redis.set(
    `oauth:rt:${refreshToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ONE_YEAR_SEC }
  );
  return res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: ACCESS_TOKEN_TTL_SEC,
    refresh_token: refreshToken,
    scope: data.scope || undefined,
  });
}

async function handleRefreshTokenGrant(req, res, clientInfo) {
  const refreshToken = req.body.refresh_token;
  if (!refreshToken) {
    return oauthError(res, 400, 'invalid_request', 'refresh_token required');
  }
  const key = `oauth:rt:${refreshToken}`;
  const raw = await redis.get(key);
  if (!raw) {
    return oauthError(res, 400, 'invalid_grant', 'refresh token invalid or expired');
  }
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return oauthError(res, 400, 'invalid_grant', 'refresh token corrupt');
  }
  if (data.clientId !== clientInfo.id) {
    return oauthError(res, 400, 'invalid_grant', 'client mismatch');
  }
  const accessToken = randomToken();
  await redis.set(
    `oauth:at:${accessToken}`,
    JSON.stringify({ userId: data.userId, clientId: clientInfo.id, scope: data.scope || '' }),
    { EX: ACCESS_TOKEN_TTL_SEC }
  );
  return res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: ACCESS_TOKEN_TTL_SEC,
    refresh_token: refreshToken,
    scope: data.scope || undefined,
  });
}

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

async function main() {
  await redis.connect();
  app.listen(PORT, () => {
    console.log(`OAuth2 server listening on ${PORT}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});