const express = require('express');
const crypto = require('crypto');
const url = require('url');

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// In-memory stores
const clients = new Map();
const authorizationCodes = new Map();
const tokens = new Map();

// Register a demo client
clients.set('demo-client', {
  client_id: 'demo-client',
  client_secret: 'demo-secret',
  redirect_uris: ['http://localhost:3001/callback']
});

// Registered redirect URIs are the source of truth — never trust user-supplied URIs alone
function validateRedirectUri(clientId, redirectUri) {
  const client = clients.get(clientId);
  if (!client) return false;
  return client.redirect_uris.includes(redirectUri);
}

function generateCode() {
  return crypto.randomBytes(32).toString('hex');
}

function generateToken() {
  return crypto.randomBytes(48).toString('hex');
}

// GET /authorize — shows consent form
app.get('/authorize', (req, res) => {
  const { response_type, client_id, redirect_uri, state, scope } = req.query;

  if (response_type !== 'code') {
    return res.status(400).send('Unsupported response_type. Must be "code".');
  }

  if (!client_id || !clients.has(client_id)) {
    return res.status(400).send('Invalid client_id.');
  }

  if (!redirect_uri || !validateRedirectUri(client_id, redirect_uri)) {
    // Do NOT redirect to an unvalidated URI — render error directly
    return res.status(400).send('Invalid or unregistered redirect_uri.');
  }

  // Render a simple consent page
  res.send(`
    <!DOCTYPE html>
    <html>
    <head><title>Authorize</title></head>
    <body>
      <h2>Authorization Request</h2>
      <p>Client <strong>${escapeHtml(client_id)}</strong> is requesting access.</p>
      <p>Scope: <strong>${escapeHtml(scope || 'default')}</strong></p>
      <form method="POST" action="/authorize">
        <input type="hidden" name="response_type" value="code" />
        <input type="hidden" name="client_id" value="${escapeHtml(client_id)}" />
        <input type="hidden" name="redirect_uri" value="${escapeHtml(redirect_uri)}" />
        <input type="hidden" name="state" value="${escapeHtml(state || '')}" />
        <input type="hidden" name="scope" value="${escapeHtml(scope || 'default')}" />
        <label>Username: <input type="text" name="username" required /></label><br/><br/>
        <button type="submit" name="action" value="approve">Approve</button>
        <button type="submit" name="action" value="deny">Deny</button>
      </form>
    </body>
    </html>
  `);
});

// POST /authorize — process consent
app.post('/authorize', (req, res) => {
  const { response_type, client_id, redirect_uri, state, scope, username, action } = req.body;

  if (!client_id || !validateRedirectUri(client_id, redirect_uri)) {
    return res.status(400).send('Invalid request.');
  }

  const redirectUrl = new URL(redirect_uri);

  if (action === 'deny') {
    redirectUrl.searchParams.set('error', 'access_denied');
    if (state) redirectUrl.searchParams.set('state', state);
    return res.redirect(redirectUrl.toString());
  }

  if (!username) {
    return res.status(400).send('Username is required.');
  }

  const code = generateCode();
  authorizationCodes.set(code, {
    client_id,
    redirect_uri,
    username,
    scope: scope || 'default',
    created_at: Date.now(),
    used: false
  });

  // Expire code after 10 minutes
  setTimeout(() => authorizationCodes.delete(code), 10 * 60 * 1000);

  redirectUrl.searchParams.set('code', code);
  if (state) redirectUrl.searchParams.set('state', state);
  res.redirect(redirectUrl.toString());
});

// POST /token — exchange code for token
app.post('/token', (req, res) => {
  const { grant_type, code, redirect_uri, client_id, client_secret } = req.body;

  if (grant_type !== 'authorization_code') {
    return res.status(400).json({ error: 'unsupported_grant_type' });
  }

  // Authenticate client
  if (!client_id || !client_secret) {
    return res.status(401).json({ error: 'invalid_client', error_description: 'Client credentials required.' });
  }

  const client = clients.get(client_id);
  if (!client || client.client_secret !== client_secret) {
    return res.status(401).json({ error: 'invalid_client' });
  }

  // Validate authorization code
  const authCode = authorizationCodes.get(code);
  if (!authCode) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Invalid or expired authorization code.' });
  }

  if (authCode.used) {
    // Code reuse attempt — revoke any tokens issued with this code
    authorizationCodes.delete(code);
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Authorization code already used.' });
  }

  if (authCode.client_id !== client_id) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Code was not issued to this client.' });
  }

  if (authCode.redirect_uri !== redirect_uri) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'redirect_uri mismatch.' });
  }

  // Mark code as used (single-use)
  authCode.used = true;

  const accessToken = generateToken();
  const tokenData = {
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: 3600,
    scope: authCode.scope,
    username: authCode.username
  };

  tokens.set(accessToken, {
    ...tokenData,
    created_at: Date.now()
  });

  // Clean up code
  authorizationCodes.delete(code);

  res.json({
    access_token: tokenData.access_token,
    token_type: tokenData.token_type,
    expires_in: tokenData.expires_in,
    scope: tokenData.scope
  });
});

// Simple token introspection endpoint
app.get('/userinfo', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'invalid_token' });
  }

  const token = authHeader.slice(7);
  const tokenData = tokens.get(token);

  if (!tokenData) {
    return res.status(401).json({ error: 'invalid_token' });
  }

  if (Date.now() - tokenData.created_at > tokenData.expires_in * 1000) {
    tokens.delete(token);
    return res.status(401).json({ error: 'token_expired' });
  }

  res.json({ username: tokenData.username, scope: tokenData.scope });
});

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`OAuth 2.0 Authorization Server running on http://localhost:${PORT}`);
  console.log(`Demo client registered: client_id=demo-client, redirect_uri=http://localhost:3001/callback`);
});