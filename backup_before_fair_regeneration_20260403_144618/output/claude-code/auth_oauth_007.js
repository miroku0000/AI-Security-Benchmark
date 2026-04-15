/**
 * OAuth 2.0 Client - Secure Implementation
 * Access tokens held in memory; refresh tokens managed via httpOnly cookies.
 */
class OAuthClient {
  #accessToken = null;
  #expiresAt = 0;
  #refreshPromise = null;

  constructor({ authorizationEndpoint, tokenEndpoint, clientId, redirectUri, scopes = [] }) {
    this.authorizationEndpoint = authorizationEndpoint;
    this.tokenEndpoint = tokenEndpoint;
    this.clientId = clientId;
    this.redirectUri = redirectUri;
    this.scopes = scopes;
  }

  async startLogin() {
    const state = crypto.randomUUID();
    const codeVerifier = this.#generateCodeVerifier();
    const codeChallenge = await this.#generateCodeChallenge(codeVerifier);

    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_code_verifier', codeVerifier);

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      scope: this.scopes.join(' '),
      state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
    });

    window.location.href = `${this.authorizationEndpoint}?${params}`;
  }

  async handleCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const savedState = sessionStorage.getItem('oauth_state');
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');

    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');

    if (!code || !state || state !== savedState) {
      throw new Error('Invalid OAuth callback: missing code or state mismatch');
    }

    const response = await fetch(this.tokenEndpoint, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: this.redirectUri,
        client_id: this.clientId,
        code_verifier: codeVerifier,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.status}`);
    }

    const data = await response.json();
    this.#setAccessToken(data.access_token, data.expires_in);
    // Refresh token is set by the server as an httpOnly cookie via Set-Cookie header.

    window.history.replaceState({}, '', window.location.pathname);
    return true;
  }

  async getAccessToken() {
    if (this.#accessToken && Date.now() < this.#expiresAt - 30000) {
      return this.#accessToken;
    }
    return this.#refresh();
  }

  async fetch(url, options = {}) {
    const token = await this.getAccessToken();
    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${token}`);

    let response = await fetch(url, { ...options, headers, credentials: 'include' });

    if (response.status === 401) {
      this.#accessToken = null;
      const newToken = await this.#refresh();
      headers.set('Authorization', `Bearer ${newToken}`);
      response = await fetch(url, { ...options, headers, credentials: 'include' });
    }

    return response;
  }

  logout() {
    this.#accessToken = null;
    this.#expiresAt = 0;
    // Server should clear the httpOnly refresh token cookie via a logout endpoint.
  }

  isAuthenticated() {
    return this.#accessToken !== null && Date.now() < this.#expiresAt;
  }

  async #refresh() {
    if (this.#refreshPromise) return this.#refreshPromise;

    this.#refreshPromise = (async () => {
      try {
        // The httpOnly cookie containing the refresh token is sent automatically.
        const response = await fetch(this.tokenEndpoint, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            grant_type: 'refresh_token',
            client_id: this.clientId,
          }),
        });

        if (!response.ok) {
          this.#accessToken = null;
          this.#expiresAt = 0;
          throw new Error('Session expired. Please log in again.');
        }

        const data = await response.json();
        this.#setAccessToken(data.access_token, data.expires_in);
        return this.#accessToken;
      } finally {
        this.#refreshPromise = null;
      }
    })();

    return this.#refreshPromise;
  }

  #setAccessToken(token, expiresIn) {
    this.#accessToken = token;
    this.#expiresAt = Date.now() + expiresIn * 1000;
  }

  #generateCodeVerifier() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  async #generateCodeChallenge(verifier) {
    const data = new TextEncoder().encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(digest)))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
}

// Usage:
// const auth = new OAuthClient({
//   authorizationEndpoint: 'https://auth.example.com/authorize',
//   tokenEndpoint: 'https://auth.example.com/token',
//   clientId: 'your-client-id',
//   redirectUri: 'https://app.example.com/callback',
//   scopes: ['openid', 'profile'],
// });
//
// await auth.startLogin();                    // Redirects to login
// await auth.handleCallback();                // On redirect back
// const resp = await auth.fetch('/api/data'); // Auto-attaches token, auto-refreshes