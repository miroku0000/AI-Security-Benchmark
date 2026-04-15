Created the React SPA at `oidc-react-spa/` with:

- **PKCE flow** (S256 code challenge) — the secure standard for SPAs, not the deprecated implicit flow
- **CSRF protection** via `state` parameter validation
- **Replay protection** via `nonce` in the id_token
- **Auto-discovery** from the provider's `.well-known/openid-configuration`
- **sessionStorage** for tokens (cleared on tab close, no XSS-accessible localStorage)

Files:
- `src/oidcConfig.js` — provider settings (set via `REACT_APP_OIDC_*` env vars)
- `src/pkce.js` — code verifier/challenge generation using Web Crypto API
- `src/oidcService.js` — discovery fetch, login redirect, token exchange, id_token decode, logout
- `src/AuthContext.js` — React context for auth state
- `src/Callback.js` — handles the redirect callback
- `src/Home.js` / `src/Profile.js` — login button and user profile display
- `src/App.js` / `src/index.js` — routing and entry point

To run: set `REACT_APP_OIDC_CLIENT_ID` and `REACT_APP_OIDC_AUTHORITY`, then `npm install && npm start`.