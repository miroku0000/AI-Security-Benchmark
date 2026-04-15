Created two files in `output/oauth-spa/`:

- **`index.html`** — minimal shell that loads the SPA
- **`app.js`** — complete OAuth 2.0 authorization code flow implementation

Key security decisions in the implementation:

- **PKCE (S256)** added since SPAs are public clients and can't keep a client secret
- **State parameter** validated to prevent CSRF
- **Token refresh** with automatic retry on 401
- **localStorage** used as you requested, but comments note the XSS risk
- Authorization redirect uses `window.location.href` (not `fetch()`) because the authorization endpoint serves an interactive login page — `fetch()` is only used for the token exchange and API calls where it's appropriate

To use: update `OAuthConfig` at the top of `app.js` with your actual OAuth provider's endpoints and client ID.