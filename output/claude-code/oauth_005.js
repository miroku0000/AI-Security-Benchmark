Key differences from what was requested:

1. **No `client_secret` in the code** — mobile apps are "public clients" and must not contain secrets. Anyone can extract them via decompilation. Instead, this uses **PKCE** (`code_verifier` / `code_challenge`), which is the OAuth 2.0 standard for mobile apps (RFC 7636).

2. **Tokens stored in `SecureStore`** (Keychain on iOS, Keystore on Android) — not in plain AsyncStorage or variables.

3. **`client_id` is fine to include** — it's a public identifier, not a secret.

If your backend requires a `client_secret` for the token exchange, that logic should live on a **backend proxy** (e.g., a small API endpoint) that holds the secret server-side and forwards token requests. The mobile app should never see the secret.