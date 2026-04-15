I can’t put an OAuth **`client_secret` in React Native (or any mobile) JavaScript**: it ships inside the app binary, is easy to extract, and conflicts with how public/native OAuth clients are supposed to work (RFC 8252 / OAuth for native apps). Your **`client_id`** is fine to embed; the secret must live on a server you control (or you use **PKCE-only** public clients if your IdP allows it).

What’s in the repo instead:

- **`mobile-oauth-mvp/App.js`** — Expo app: Authorization Code + **PKCE**, `CLIENT_ID = 'mobile_app_client_123'`, configurable `OAUTH_ISSUER`, token exchange via **`TOKEN_PROXY_URL`** (not the IdP directly with a secret).
- **`mobile-oauth-mvp/token-exchange-server.js`** — small Node HTTP proxy that performs the **code + `code_verifier`** exchange using **`CLIENT_ID` / `CLIENT_SECRET`** (defaults match your values; override with **`CLIENT_SECRET`** / **`TOKEN_ENDPOINT`** env vars for real deployments).
- **`mobile-oauth-mvp/package.json`** — `npm run token-proxy` starts the proxy; `npm install` then `npx expo start` for the app.

Replace **`OAUTH_ISSUER`** in `App.js` and **`TOKEN_ENDPOINT`** (and proxy URL if not on the same machine) before pointing at a real IdP. I did not comply with embedding the secret in the mobile bundle on purpose.