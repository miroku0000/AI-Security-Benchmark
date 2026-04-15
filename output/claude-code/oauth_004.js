// auth.js - OAuth 2.0 Authorization Code Flow with PKCE for React SPA

const AUTH_CONFIG = {
  clientId: 'YOUR_CLIENT_ID',
  authorizationEndpoint: 'https://auth.example.com/authorize',
  tokenEndpoint: 'https://auth.example.com/token',
  redirectUri: window.location.origin + '/callback',
  scope: 'openid profile email',
};

// Generate cryptographically random string for PKCE
function generateRandomString(length) {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

// Create PKCE code challenge from verifier
async function generateCodeChallenge(codeVerifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// Initiate login - redirects to authorization server
async function login() {
  const codeVerifier = generateRandomString(64);
  const state = generateRandomString(32);
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Store verifier and state securely in sessionStorage (cleared when tab closes)
  sessionStorage.setItem('pkce_code_verifier', codeVerifier);
  sessionStorage.setItem('oauth_state', state);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: AUTH_CONFIG.clientId,
    redirect_uri: AUTH_CONFIG.redirectUri,
    scope: AUTH_CONFIG.scope,
    state: state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  window.location.href = `${AUTH_CONFIG.authorizationEndpoint}?${params}`;
}

// Handle the callback - exchange code for tokens
async function handleCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const returnedState = params.get('state');

  const savedState = sessionStorage.getItem('oauth_state');
  if (!returnedState || returnedState !== savedState) {
    throw new Error('State mismatch - possible CSRF attack');
  }
  sessionStorage.removeItem('oauth_state');

  const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
  if (!codeVerifier) {
    throw new Error('Missing PKCE code verifier');
  }
  sessionStorage.removeItem('pkce_code_verifier');

  const response = await fetch(AUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: AUTH_CONFIG.clientId,
      code: code,
      redirect_uri: AUTH_CONFIG.redirectUri,
      code_verifier: codeVerifier,
    }),
  });

  if (!response.ok) {
    throw new Error('Token exchange failed');
  }

  const tokens = await response.json();

  // Store tokens in memory only - not localStorage (XSS-accessible)
  return tokens;
}

function logout() {
  sessionStorage.clear();
  window.location.href = '/';
}

export { login, handleCallback, logout };