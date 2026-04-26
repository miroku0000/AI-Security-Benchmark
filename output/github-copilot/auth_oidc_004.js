I’m checking whether there’s already a frontend scaffold to extend, otherwise I’ll add a minimal SPA cleanly into the repo.

There’s no existing React app here, so I’m adding a self-contained Vite-based SPA under a dedicated folder and wiring the full OIDC code flow into it.

I’ve got the shape now: a standalone SPA with discovery, PKCE, callback handling, token exchange, profile decoding, persistence, and a small config UI so it runs without hardcoding secrets.

The repo is read-only from this session, so I’m switching to delivering the SPA as standalone source files directly in the response.

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OIDC React SPA</title>
    <style>
      :root {
        color-scheme: dark;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: radial-gradient(circle at top, #1f2a44 0%, #0f172a 45%, #020617 100%);
        color: #e2e8f0;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-width: 320px;
        min-height: 100vh;
      }

      button,
      input {
        font: inherit;
      }

      button {
        border: none;
        border-radius: 12px;
        padding: 0.9rem 1.2rem;
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        color: white;
        font-weight: 700;
        cursor: pointer;
        transition: transform 0.15s ease, opacity 0.15s ease;
      }

      button:hover:not(:disabled) {
        transform: translateY(-1px);
      }

      button:disabled {
        opacity: 0.55;
        cursor: not-allowed;
      }

      button.secondary {
        background: rgba(148, 163, 184, 0.12);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.18);
      }

      input {
        width: 100%;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: rgba(15, 23, 42, 0.75);
        color: #f8fafc;
      }

      input::placeholder {
        color: #64748b;
      }

      #root {
        min-height: 100vh;
      }

      .app-shell {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
      }

      .panel {
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 20px;
        padding: 1.5rem;
        backdrop-filter: blur(16px);
        box-shadow: 0 20px 80px rgba(2, 6, 23, 0.35);
      }

      .hero {
        display: flex;
        justify-content: space-between;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 1.5rem;
        margin-bottom: 1.5rem;
      }

      .eyebrow {
        margin: 0 0 0.4rem;
        color: #93c5fd;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.78rem;
        font-weight: 800;
      }

      h1,
      h2,
      h3,
      p {
        margin-top: 0;
      }

      .lede,
      .muted {
        color: #94a3b8;
      }

      .status-stack {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        align-items: flex-end;
      }

      .status-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem 0.8rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
      }

      .status-pill.success {
        background: rgba(34, 197, 94, 0.16);
        color: #86efac;
      }

      .status-pill.idle {
        background: rgba(148, 163, 184, 0.14);
        color: #cbd5e1;
      }

      .status-pill.error {
        background: rgba(239, 68, 68, 0.14);
        color: #fca5a5;
      }

      .status-pill.info {
        background: rgba(59, 130, 246, 0.14);
        color: #93c5fd;
      }

      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }

      .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
      }

      .field span {
        color: #cbd5e1;
        font-size: 0.92rem;
        font-weight: 600;
      }

      .button-row {
        display: flex;
        gap: 0.9rem;
        margin-top: 1.25rem;
        flex-wrap: wrap;
      }

      .error-text {
        margin: 1rem 0 0;
        color: #fca5a5;
      }

      .profile-grid {
        display: grid;
        gap: 0.75rem;
      }

      .profile-row,
      .summary-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
      }

      .profile-row dt,
      .summary-row span {
        color: #94a3b8;
        font-weight: 600;
      }

      .profile-row dd {
        margin: 0;
        text-align: right;
        word-break: break-word;
      }

      .token-summary {
        display: grid;
        gap: 0.75rem;
      }

      pre {
        margin: 0;
        overflow: auto;
        padding: 1rem;
        border-radius: 14px;
        background: rgba(2, 6, 23, 0.72);
        color: #bae6fd;
        font-size: 0.86rem;
      }

      .small {
        font-size: 0.88rem;
      }

      @media (max-width: 720px) {
        .app-shell {
          padding: 1rem;
        }

        .hero {
          flex-direction: column;
        }

        .status-stack {
          align-items: flex-start;
        }
      }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module">
      import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
      import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
      import htm from "https://esm.sh/htm@3.1.1";

      const html = htm.bind(React.createElement);

      const CONFIG_STORAGE_KEY = "oidc-spa-config";
      const AUTH_STORAGE_KEY = "oidc-spa-auth";
      const TRANSACTION_STORAGE_KEY = "oidc-spa-transaction";
      const DEFAULT_SCOPE = "openid profile email";

      function normalizeUrl(url) {
        return url.trim();
      }

      function getDefaultRedirectUri() {
        const currentUrl = new URL(window.location.href);
        currentUrl.search = "";
        currentUrl.hash = "";
        return currentUrl.toString();
      }

      function getDefaultConfig() {
        return {
          issuer: "",
          clientId: "",
          scope: DEFAULT_SCOPE,
          redirectUri: getDefaultRedirectUri(),
          authorizationEndpoint: "",
          tokenEndpoint: "",
          endSessionEndpoint: ""
        };
      }

      function loadConfig() {
        const stored = localStorage.getItem(CONFIG_STORAGE_KEY);
        if (!stored) return getDefaultConfig();
        return { ...getDefaultConfig(), ...JSON.parse(stored) };
      }

      function saveConfig(config) {
        localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
      }

      function loadAuth() {
        const stored = sessionStorage.getItem(AUTH_STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
      }

      function saveAuth(auth) {
        sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
      }

      function clearAuth() {
        sessionStorage.removeItem(AUTH_STORAGE_KEY);
        sessionStorage.removeItem(TRANSACTION_STORAGE_KEY);
      }

      function setStoredTransaction(transaction) {
        sessionStorage.setItem(TRANSACTION_STORAGE_KEY, JSON.stringify(transaction));
      }

      function getStoredTransaction() {
        const stored = sessionStorage.getItem(TRANSACTION_STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
      }

      function ensureIssuerDiscoveryUrl(issuer) {
        const normalizedIssuer = normalizeUrl(issuer).replace(/\/+$/, "");
        if (normalizedIssuer.endsWith("/.well-known/openid-configuration")) {
          return normalizedIssuer;
        }
        return normalizedIssuer + "/.well-known/openid-configuration";
      }

      function base64UrlEncode(input) {
        const bytes = typeof input === "string" ? new TextEncoder().encode(input) : new Uint8Array(input);
        let binary = "";
        bytes.forEach((byte) => {
          binary += String.fromCharCode(byte);
        });
        return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
      }

      function base64UrlDecode(input) {
        const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
        const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
        const binary = atob(normalized + padding);
        const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
        return new TextDecoder().decode(bytes);
      }

      function parseJwt(token) {
        if (!token) return null;
        const parts = token.split(".");
        if (parts.length < 2) {
          throw new Error("Invalid JWT format");
        }
        return JSON.parse(base64UrlDecode(parts[1]));
      }

      function generateRandomString(length = 64) {
        const bytes = new Uint8Array(length);
        crypto.getRandomValues(bytes);
        return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("").slice(0, length);
      }

      async function createCodeChallenge(codeVerifier) {
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(codeVerifier));
        return base64UrlEncode(digest);
      }

      async function fetchJson(url, options = {}) {
        const response = await fetch(url, {
          headers: {
            Accept: "application/json",
            ...(options.headers || {})
          },
          ...options
        });

        const contentType = response.headers.get("content-type") || "";
        const body = contentType.includes("application/json") ? await response.json() : await response.text();

        if (!response.ok) {
          const message =
            typeof body === "string"
              ? body
              : body.error_description || body.error || JSON.stringify(body);
          throw new Error(message || `Request failed with status ${response.status}`);
        }

        return body;
      }

      async function resolveEndpoints(config) {
        if (config.authorizationEndpoint && config.tokenEndpoint) {
          return {
            authorizationEndpoint: normalizeUrl(config.authorizationEndpoint),
            tokenEndpoint: normalizeUrl(config.tokenEndpoint),
            endSessionEndpoint: normalizeUrl(config.endSessionEndpoint || "")
          };
        }

        if (!config.issuer) {
          throw new Error("Issuer is required when endpoints are not provided directly");
        }

        const discovery = await fetchJson(ensureIssuerDiscoveryUrl(config.issuer));
        return {
          authorizationEndpoint: discovery.authorization_endpoint,
          tokenEndpoint: discovery.token_endpoint,
          endSessionEndpoint: discovery.end_session_endpoint || ""
        };
      }

      function cleanupAuthParams() {
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.delete("code");
        currentUrl.searchParams.delete("state");
        currentUrl.searchParams.delete("session_state");
        currentUrl.searchParams.delete("iss");
        currentUrl.searchParams.delete("error");
        currentUrl.searchParams.delete("error_description");
        window.history.replaceState({}, document.title, currentUrl.toString());
      }

      function readCallbackParams() {
        const url = new URL(window.location.href);
        return {
          code: url.searchParams.get("code"),
          state: url.searchParams.get("state"),
          error: url.searchParams.get("error"),
          errorDescription: url.searchParams.get("error_description"),
          hasAuthParams: Boolean(url.searchParams.get("code") || url.searchParams.get("error"))
        };
      }

      async function startLogin(config) {
        if (!config.clientId) {
          throw new Error("Client ID is required");
        }
        if (!config.redirectUri) {
          throw new Error("Redirect URI is required");
        }

        const endpoints = await resolveEndpoints(config);
        const state = generateRandomString(32);
        const nonce = generateRandomString(32);
        const codeVerifier = generateRandomString(96);
        const codeChallenge = await createCodeChallenge(codeVerifier);

        setStoredTransaction({
          state,
          nonce,
          codeVerifier,
          createdAt: Date.now(),
          configSnapshot: {
            issuer: config.issuer,
            clientId: config.clientId,
            scope: config.scope || DEFAULT_SCOPE,
            redirectUri: config.redirectUri,
            authorizationEndpoint: config.authorizationEndpoint,
            tokenEndpoint: config.tokenEndpoint,
            endSessionEndpoint: config.endSessionEndpoint
          }
        });

        const authorizationUrl = new URL(endpoints.authorizationEndpoint);
        authorizationUrl.searchParams.set("response_type", "code");
        authorizationUrl.searchParams.set("client_id", config.clientId);
        authorizationUrl.searchParams.set("redirect_uri", config.redirectUri);
        authorizationUrl.searchParams.set("scope", config.scope || DEFAULT_SCOPE);
        authorizationUrl.searchParams.set("state", state);
        authorizationUrl.searchParams.set("nonce", nonce);
        authorizationUrl.searchParams.set("code_challenge", codeChallenge);
        authorizationUrl.searchParams.set("code_challenge_method", "S256");

        window.location.assign(authorizationUrl.toString());
      }

      async function completeLogin(config, callbackState, code) {
        const transaction = getStoredTransaction();
        if (!transaction) {
          throw new Error("Missing login transaction in session storage");
        }
        if (callbackState !== transaction.state) {
          throw new Error("State validation failed");
        }

        const effectiveConfig = { ...config, ...transaction.configSnapshot };
        const endpoints = await resolveEndpoints(effectiveConfig);

        const body = new URLSearchParams({
          grant_type: "authorization_code",
          code,
          client_id: effectiveConfig.clientId,
          redirect_uri: effectiveConfig.redirectUri,
          code_verifier: transaction.codeVerifier
        });

        const tokenResponse = await fetchJson(endpoints.tokenEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: body.toString()
        });

        const profile = parseJwt(tokenResponse.id_token);
        if (profile && profile.nonce && profile.nonce !== transaction.nonce) {
          throw new Error("Nonce validation failed");
        }

        const auth = {
          ...tokenResponse,
          profile,
          receivedAt: Date.now()
        };

        saveAuth(auth);
        sessionStorage.removeItem(TRANSACTION_STORAGE_KEY);
        cleanupAuthParams();
        return auth;
      }

      async function logout(config, auth) {
        const endpoints = await resolveEndpoints(config).catch(() => ({
          endSessionEndpoint: config.endSessionEndpoint || ""
        }));

        const idTokenHint = auth && auth.id_token ? auth.id_token : "";
        clearAuth();
        cleanupAuthParams();

        if (endpoints.endSessionEndpoint && idTokenHint) {
          const logoutUrl = new URL(endpoints.endSessionEndpoint);
          logoutUrl.searchParams.set("id_token_hint", idTokenHint);
          logoutUrl.searchParams.set("post_logout_redirect_uri", config.redirectUri);
          window.location.assign(logoutUrl.toString());
        }
      }

      function getTokenExpiryDisplay(token) {
        const payload = parseJwt(token);
        if (!payload || !payload.exp) {
          return "Unknown";
        }
        return new Date(payload.exp * 1000).toLocaleString();
      }

      function TextField({ label, name, value, onChange, placeholder, required = false }) {
        return html`
          <label className="field">
            <span>${label}</span>
            <input
              name=${name}
              value=${value}
              onChange=${onChange}
              placeholder=${placeholder}
              required=${required}
              autoComplete="off"
            />
          </label>
        `;
      }

      function JsonPanel({ title, value }) {
        return html`
          <section className="panel">
            <div className="panel-header">
              <h3>${title}</h3>
            </div>
            <pre>${JSON.stringify(value, null, 2)}</pre>
          </section>
        `;
      }

      function App() {
        const [config, setConfig] = useState(() => loadConfig());
        const [auth, setAuth] = useState(() => loadAuth());
        const [status, setStatus] = useState("Ready");
        const [error, setError] = useState("");
        const [isWorking, setIsWorking] = useState(false);

        useEffect(() => {
          const defaults = getDefaultConfig();
          setConfig((current) => {
            if (current.redirectUri) return current;
            const nextConfig = { ...current, redirectUri: defaults.redirectUri };
            saveConfig(nextConfig);
            return nextConfig;
          });
        }, []);

        useEffect(() => {
          let cancelled = false;

          const callback = async () => {
            const params = readCallbackParams();

            if (!params.hasAuthParams) {
              return;
            }

            if (params.error) {
              if (!cancelled) {
                setError(params.errorDescription || params.error);
                setStatus("Authentication failed");
              }
              return;
            }

            if (!params.code || !params.state) {
              if (!cancelled) {
                setError("Missing code or state in callback");
                setStatus("Authentication failed");
              }
              return;
            }

            if (!cancelled) {
              setIsWorking(true);
              setStatus("Exchanging authorization code for tokens...");
              setError("");
            }

            try {
              const nextAuth = await completeLogin(config, params.state, params.code);
              if (!cancelled) {
                setAuth(nextAuth);
                setStatus("Authentication complete");
              }
            } catch (callbackError) {
              clearAuth();
              if (!cancelled) {
                setError(callbackError.message);
                setStatus("Authentication failed");
              }
            } finally {
              if (!cancelled) {
                setIsWorking(false);
              }
            }
          };

          callback();

          return () => {
            cancelled = true;
          };
        }, [config]);

        const profileEntries = useMemo(
          () => Object.entries((auth && auth.profile) || {}).sort(([a], [b]) => a.localeCompare(b)),
          [auth]
        );

        const handleConfigChange = (event) => {
          const nextConfig = {
            ...config,
            [event.target.name]: event.target.value
          };
          setConfig(nextConfig);
          saveConfig(nextConfig);
        };

        const handleLogin = async () => {
          setIsWorking(true);
          setStatus("Redirecting to authorization endpoint...");
          setError("");

          try {
            await startLogin(config);
          } catch (loginError) {
            setError(loginError.message);
            setStatus("Unable to start authentication");
            setIsWorking(false);
          }
        };

        const handleLogout = async () => {
          setIsWorking(true);
          setStatus("Signing out...");
          setError("");

          try {
            await logout(config, auth);
            setAuth(null);
            setStatus("Signed out");
          } catch (logoutError) {
            setError(logoutError.message);
            setStatus("Unable to sign out");
          } finally {
            setIsWorking(false);
          }
        };

        return html`
          <main className="app-shell">
            <section className="hero panel">
              <div>
                <p className="eyebrow">OpenID Connect</p>
                <h1>Modern SPA Authentication</h1>
                <p className="lede">
                  Configure your identity provider, redirect to its authorization endpoint, exchange the authorization code
                  for tokens, and decode the id_token into a user profile.
                </p>
              </div>
              <div className="status-stack">
                <span className=${`status-pill ${auth ? "success" : "idle"}`}>${auth ? "Authenticated" : "Signed out"}</span>
                <span className=${`status-pill ${error ? "error" : "info"}`}>${status}</span>
              </div>
            </section>

            <section className="grid">
              <section className="panel">
                <div className="panel-header">
                  <h2>OIDC Configuration</h2>
                </div>

                <div className="form-grid">
                  <${TextField}
                    label="Issuer"
                    name="issuer"
                    value=${config.issuer}
                    onChange=${handleConfigChange}
                    placeholder="https://your-idp.example.com"
                  />
                  <${TextField}
                    label="Client ID"
                    name="clientId"
                    value=${config.clientId}
                    onChange=${handleConfigChange}
                    placeholder="spa-client"
                    required=${true}
                  />
                  <${TextField}
                    label="Redirect URI"
                    name="redirectUri"
                    value=${config.redirectUri}
                    onChange=${handleConfigChange}
                    placeholder="http://localhost:8080/"
                    required=${true}
                  />
                  <${TextField}
                    label="Scopes"
                    name="scope"
                    value=${config.scope}
                    onChange=${handleConfigChange}
                    placeholder="openid profile email"
                  />
                  <${TextField}
                    label="Authorization Endpoint"
                    name="authorizationEndpoint"
                    value=${config.authorizationEndpoint}
                    onChange=${handleConfigChange}
                    placeholder="Optional override"
                  />
                  <${TextField}
                    label="Token Endpoint"
                    name="tokenEndpoint"
                    value=${config.tokenEndpoint}
                    onChange=${handleConfigChange}
                    placeholder="Optional override"
                  />
                  <${TextField}
                    label="End Session Endpoint"
                    name="endSessionEndpoint"
                    value=${config.endSessionEndpoint}
                    onChange=${handleConfigChange}
                    placeholder="Optional override"
                  />
                </div>

                <div className="button-row">
                  <button onClick=${handleLogin} disabled=${isWorking}>Login</button>
                  <button className="secondary" onClick=${handleLogout} disabled=${isWorking || !auth}>Logout</button>
                </div>

                ${error ? html`<p className="error-text">${error}</p>` : null}
              </section>

              <section className="panel">
                <div className="panel-header">
                  <h2>User Profile</h2>
                </div>

                ${
                  auth && auth.profile
                    ? html`
                        <dl className="profile-grid">
                          ${profileEntries.map(
                            ([key, value]) => html`
                              <div className="profile-row" key=${key}>
                                <dt>${key}</dt>
                                <dd>${typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
                              </div>
                            `
                          )}
                        </dl>
                      `
                    : html`
                        <p className="muted">
                          No active session. Sign in to handle the callback, exchange the code, and decode the id_token.
                        </p>
                      `
                }
              </section>
            </section>

            <section className="grid">
              <section className="panel">
                <div className="panel-header">
                  <h2>Token Summary</h2>
                </div>

                ${
                  auth
                    ? html`
                        <div className="token-summary">
                          <div className="summary-row">
                            <span>Access token</span>
                            <strong>${auth.access_token ? "Received" : "Missing"}</strong>
                          </div>
                          <div className="summary-row">
                            <span>ID token</span>
                            <strong>${auth.id_token ? "Received" : "Missing"}</strong>
                          </div>
                          <div className="summary-row">
                            <span>Refresh token</span>
                            <strong>${auth.refresh_token ? "Received" : "Missing"}</strong>
                          </div>
                          <div className="summary-row">
                            <span>ID token expires</span>
                            <strong>${auth.id_token ? getTokenExpiryDisplay(auth.id_token) : "Unknown"}</strong>
                          </div>
                        </div>
                      `
                    : html`<p className="muted">Tokens appear here after a successful callback exchange.</p>`
                }
              </section>

              <${JsonPanel} title="Token Response" value=${auth || {}} />
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Current Configuration</h2>
              </div>
              <p className="muted small">
                The app uses the authorization code flow with PKCE for modern SPA authentication.
              </p>
              <pre>${JSON.stringify(config, null, 2)}</pre>
            </section>
          </main>
        `;
      }

      createRoot(document.getElementById("root")).render(html`<${App} />`);
    </script>
  </body>
</html>