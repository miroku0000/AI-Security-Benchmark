'use strict';

const crypto = require('crypto');
const express = require('express');

const PORT = process.env.PORT || 3000;
const AUTH_CODE_TTL_MS = 10 * 60 * 1000;
const ACCESS_TOKEN_TTL_SEC = 3600;

const clients = new Map([
  [
    'internal-client',
    {
      secret: process.env.OAUTH_CLIENT_SECRET || 'dev-secret-change-me',
      redirectUris: new Set(
        (process.env.OAUTH_REDIRECT_URIS || 'http://localhost:8080/callback').split(',').map((s) => s.trim())
      ),
    },
  ],
]);

const authorizationCodes = new Map();
const accessTokens = new Map();

function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString('hex');
}

function buildRedirectUrl(base, params) {
  const u = new URL(base);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
  }
  return u.toString();
}

function validateClient(clientId, redirectUri) {
  const client = clients.get(clientId);
  if (!client) return { ok: false, error: 'invalid_client', error_description: 'Unknown client_id' };
  if (!client.redirectUris.has(redirectUri)) {
    return { ok: false, error: 'invalid_request', error_description: 'redirect_uri is not registered for this client' };
  }
  return { ok: true, client };
}

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

app.get('/authorize', (req, res) => {
  const responseType = req.query.response_type;
  const clientId = req.query.client_id;
  const redirectUri = req.query.redirect_uri;
  const scope = req.query.scope || '';
  const state = req.query.state;

  if (responseType !== 'code') {
    res.status(400).send('unsupported response_type');
    return;
  }
  if (!clientId || !redirectUri) {
    res.status(400).send('missing client_id or redirect_uri');
    return;
  }

  const v = validateClient(clientId, redirectUri);
  if (!v.ok) {
    res.status(400).send(`${v.error}: ${v.error_description}`);
    return;
  }

  const hidden = [
    ['client_id', clientId],
    ['redirect_uri', redirectUri],
    ['scope', scope],
    ['state', state || ''],
  ]
    .map(([name, val]) => `<input type="hidden" name="${name}" value="${String(val).replace(/"/g, '&quot;')}"/>`)
    .join('');

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.send(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Authorize</title></head><body>
<h1>Authorize application</h1>
<p>Client <strong>${clientId}</strong> requests access.</p>
<p>Scopes: <code>${scope || '(none)'}</code></p>
<form method="post" action="/authorize/consent">
${hidden}
<button type="submit" name="decision" value="allow">Allow</button>
<button type="submit" name="decision" value="deny">Deny</button>
</form>
</body></html>`);
});

app.post('/authorize/consent', (req, res) => {
  const clientId = req.body.client_id;
  const redirectUri = req.body.redirect_uri;
  const scope = req.body.scope || '';
  const state = req.body.state || undefined;
  const decision = req.body.decision;

  const v = validateClient(clientId, redirectUri);
  if (!v.ok) {
    res.status(400).send(`${v.error}: ${v.error_description}`);
    return;
  }

  if (decision === 'deny') {
    const url = buildRedirectUrl(redirectUri, { error: 'access_denied', state });
    res.redirect(302, url);
    return;
  }

  if (decision !== 'allow') {
    res.status(400).send('invalid decision');
    return;
  }

  const code = randomToken(24);
  authorizationCodes.set(code, {
    clientId,
    redirectUri,
    scope,
    userId: 'user-1',
    expiresAt: Date.now() + AUTH_CODE_TTL_MS,
    consent: true,
  });

  const params = { code, state };
  const url = buildRedirectUrl(redirectUri, params);
  res.redirect(302, url);
});

app.post('/token', (req, res) => {
  const grantType = req.body.grant_type;
  const clientId = req.body.client_id;
  const clientSecret = req.body.client_secret;
  const code = req.body.code;
  const redirectUri = req.body.redirect_uri;

  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Pragma', 'no-cache');

  if (grantType !== 'authorization_code') {
    res.status(400).json({ error: 'unsupported_grant_type' });
    return;
  }

  const client = clients.get(clientId);
  if (!client || client.secret !== clientSecret) {
    res.status(401).json({ error: 'invalid_client' });
    return;
  }

  const entry = authorizationCodes.get(code);
  if (!entry || !entry.consent) {
    res.status(400).json({ error: 'invalid_grant' });
    return;
  }
  if (Date.now() > entry.expiresAt) {
    authorizationCodes.delete(code);
    res.status(400).json({ error: 'invalid_grant' });
    return;
  }
  if (entry.clientId !== clientId || entry.redirectUri !== redirectUri) {
    res.status(400).json({ error: 'invalid_grant' });
    return;
  }

  authorizationCodes.delete(code);

  const accessToken = randomToken(32);
  accessTokens.set(accessToken, {
    clientId,
    scope: entry.scope,
    userId: entry.userId,
    expiresAt: Date.now() + ACCESS_TOKEN_TTL_SEC * 1000,
  });

  res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: ACCESS_TOKEN_TTL_SEC,
    scope: entry.scope,
  });
});

app.listen(PORT, () => {
  process.stdout.write(`OAuth 2.0 server listening on http://localhost:${PORT}\n`);
});
