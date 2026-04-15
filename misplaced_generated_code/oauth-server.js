const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const PORT = process.env.PORT || 3000;

// --- Registered clients ---
const clients = new Map([
  ['webapp-portal', {
    secret: 'portal-secret-change-in-production',
    redirectUris: ['http://localhost:3001/callback']
  }],
  ['internal-dashboard', {
    secret: 'dashboard-secret-change-in-production',
    redirectUris: ['http://localhost:3002/callback']
  }]
]);

// --- Users (replace with real user store) ---
const users = new Map([
  ['admin', { password: 'admin123', name: 'Admin User', email: 'admin@corp.internal' }],
  ['jdoe', { password: 'jdoe-pass', name: 'Jane Doe', email: 'jdoe@corp.internal' }]
]);

// --- In-memory stores ---
const authorizationCodes = new Map();
const accessTokens = new Map();

const CODE_LIFETIME_MS = 10 * 60 * 1000;
const TOKEN_LIFETIME_MS = 60 * 60 * 1000;

// --- Helpers ---
function generateSecureToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString('hex');
}

function validateClient(clientId, redirectUri) {
  const client = clients.get(clientId);
  if (!client) return { valid: false, error: 'invalid_client', description: 'Unknown client_id' };
  if (!client.redirectUris.includes(redirectUri)) {
    return { valid: false, error: 'invalid_request', description: 'Unregistered redirect_uri' };
  }
  return { valid: true, client };
}

function cleanExpired() {
  const now = Date.now();
  for (const [code, data] of authorizationCodes) {
    if (now > data.expiresAt) authorizationCodes.delete(code);
  }
  for (const [token, data] of accessTokens) {
    if (now > data.expiresAt) accessTokens.delete(token);
  }
}

setInterval(cleanExpired, 60 * 1000);

// --- GET /authorize — show login form ---
app.get('/authorize', (req, res) => {
  const { client_id, redirect_uri, state, response_type, scope } = req.query;

  if (response_type !== 'code') {
    return res.status(400).json({ error: 'unsupported_response_type' });
  }

  const validation = validateClient(client_id, redirect_uri);
  if (!validation.valid) {
    return res.status(400).json({ error: validation.error, error_description: validation.description });
  }

  if (!state) {
    return res.status(400).json({ error: 'invalid_request', error_description: 'state parameter is required' });
  }

  res.type('html').send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SSO Login</title>
  <style>
    body { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f0f2f5; }
    .card { background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 320px; }
    h2 { margin-top: 0; text-align: center; }
    label { display: block; margin-top: 1rem; font-size: 0.9rem; }
    input[type=text], input[type=password] { width: 100%; padding: 0.5rem; margin-top: 0.25rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
    button { width: 100%; margin-top: 1.5rem; padding: 0.6rem; background: #1a73e8; color: #fff; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #1557b0; }
    .error { color: #d93025; font-size: 0.85rem; margin-top: 0.5rem; }
    .client-name { text-align: center; color: #555; font-size: 0.9rem; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Sign In</h2>
    <p class="client-name">Signing in to <strong>${client_id.replace(/[<>"'&]/g, '')}</strong></p>
    <form method="POST" action="/authorize">
      <input type="hidden" name="client_id" value="${client_id.replace(/"/g, '&quot;')}">
      <input type="hidden" name="redirect_uri" value="${redirect_uri.replace(/"/g, '&quot;')}">
      <input type="hidden" name="state" value="${state.replace(/"/g, '&quot;')}">
      <input type="hidden" name="scope" value="${(scope || '').replace(/"/g, '&quot;')}">
      <label>Username
        <input type="text" name="username" required autofocus>
      </label>
      <label>Password
        <input type="password" name="password" required>
      </label>
      <button type="submit">Sign In</button>
    </form>
  </div>
</body>
</html>`);
});

// --- POST /authorize — authenticate and issue code ---
app.post('/authorize', (req, res) => {
  const { client_id, redirect_uri, state, scope, username, password } = req.body;

  const validation = validateClient(client_id, redirect_uri);
  if (!validation.valid) {
    return res.status(400).json({ error: validation.error, error_description: validation.description });
  }

  const user = users.get(username);
  if (!user || user.password !== password) {
    return res.type('html').status(401).send(`<!DOCTYPE html>
<html><head><title>Login Failed</title>
<style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f0f2f5}.card{background:#fff;padding:2rem;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);width:320px;text-align:center}.error{color:#d93025}a{color:#1a73e8}</style>
</head><body><div class="card"><h2 class="error">Login Failed</h2><p>Invalid username or password.</p><a href="/authorize?response_type=code&client_id=${encodeURIComponent(client_id)}&redirect_uri=${encodeURIComponent(redirect_uri)}&state=${encodeURIComponent(state)}&scope=${encodeURIComponent(scope || '')}">Try again</a></div></body></html>`);
  }

  const code = generateSecureToken();
  authorizationCodes.set(code, {
    clientId: client_id,
    redirectUri: redirect_uri,
    username,
    scope: scope || '',
    expiresAt: Date.now() + CODE_LIFETIME_MS
  });

  const redirectUrl = new URL(redirect_uri);
  redirectUrl.searchParams.set('code', code);
  redirectUrl.searchParams.set('state', state);
  res.redirect(redirectUrl.toString());
});

// --- POST /token — exchange code for access token ---
app.post('/token', (req, res) => {
  const { grant_type, code, redirect_uri, client_id, client_secret } = req.body;

  if (grant_type !== 'authorization_code') {
    return res.status(400).json({ error: 'unsupported_grant_type' });
  }

  const client = clients.get(client_id);
  if (!client || client.secret !== client_secret) {
    return res.status(401).json({ error: 'invalid_client' });
  }

  const authCode = authorizationCodes.get(code);
  if (!authCode) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Unknown or expired authorization code' });
  }

  // One-time use: delete immediately
  authorizationCodes.delete(code);

  if (Date.now() > authCode.expiresAt) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Authorization code expired' });
  }

  if (authCode.clientId !== client_id) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'Code was not issued to this client' });
  }

  if (authCode.redirectUri !== redirect_uri) {
    return res.status(400).json({ error: 'invalid_grant', error_description: 'redirect_uri mismatch' });
  }

  const accessToken = generateSecureToken();
  const expiresIn = TOKEN_LIFETIME_MS / 1000;

  accessTokens.set(accessToken, {
    clientId: client_id,
    username: authCode.username,
    scope: authCode.scope,
    expiresAt: Date.now() + TOKEN_LIFETIME_MS
  });

  res.json({
    access_token: accessToken,
    token_type: 'Bearer',
    expires_in: expiresIn,
    scope: authCode.scope
  });
});

// --- GET /userinfo — return authenticated user info ---
app.get('/userinfo', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'invalid_token' });
  }

  const token = authHeader.slice(7);
  const tokenData = accessTokens.get(token);

  if (!tokenData || Date.now() > tokenData.expiresAt) {
    accessTokens.delete(token);
    return res.status(401).json({ error: 'invalid_token', error_description: 'Token expired or invalid' });
  }

  const user = users.get(tokenData.username);
  res.json({
    sub: tokenData.username,
    name: user.name,
    email: user.email,
    scope: tokenData.scope
  });
});

// --- POST /token/revoke — revoke an access token ---
app.post('/token/revoke', (req, res) => {
  const { token, client_id, client_secret } = req.body;

  const client = clients.get(client_id);
  if (!client || client.secret !== client_secret) {
    return res.status(401).json({ error: 'invalid_client' });
  }

  accessTokens.delete(token);
  res.status(200).json({ revoked: true });
});

app.listen(PORT, () => {
  console.log(`OAuth 2.0 Authorization Server running on http://localhost:${PORT}`);
  console.log('Endpoints:');
  console.log('  GET  /authorize   — start authorization code flow');
  console.log('  POST /authorize   — authenticate user');
  console.log('  POST /token       — exchange code for access token');
  console.log('  GET  /userinfo    — get user profile with Bearer token');
  console.log('  POST /token/revoke — revoke an access token');
});
