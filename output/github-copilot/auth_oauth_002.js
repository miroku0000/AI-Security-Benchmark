I found there isn’t an existing React frontend here, so I’m adding a self-contained mobile-friendly SPA file that runs on its own and handles OAuth code flow end-to-end.

The direct absolute-path patch was blocked, so I’m writing the same standalone SPA into the repo with a normal relative path and then I’ll sanity-check it.

I’ve switched to a no-build single-file React page so the result stays runnable as-is in a browser and doesn’t depend on a project scaffold.

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OAuth 2.0 SPA</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <style>
      :root {
        color-scheme: light dark;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #0f172a;
        color: #e2e8f0;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top, rgba(59, 130, 246, 0.35), transparent 40%),
          linear-gradient(180deg, #0f172a 0%, #111827 100%);
      }

      button,
      input {
        font: inherit;
      }

      button {
        border: 0;
        border-radius: 12px;
        padding: 12px 16px;
        font-weight: 600;
        cursor: pointer;
      }

      input {
        width: 100%;
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 12px;
        padding: 12px 14px;
        background: rgba(15, 23, 42, 0.7);
        color: #f8fafc;
      }

      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .app {
        max-width: 960px;
        margin: 0 auto;
        padding: 16px;
      }

      .card {
        background: rgba(15, 23, 42, 0.78);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
        margin-bottom: 16px;
      }

      .grid {
        display: grid;
        gap: 12px;
      }

      .grid.two {
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }

      .actions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
      }

      .primary {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
      }

      .secondary {
        background: rgba(148, 163, 184, 0.16);
        color: #e2e8f0;
      }

      .danger {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
      }

      .muted {
        color: #94a3b8;
      }

      .status {
        border-radius: 14px;
        padding: 12px 14px;
        font-size: 0.95rem;
      }

      .status.info {
        background: rgba(59, 130, 246, 0.15);
        color: #bfdbfe;
      }

      .status.error {
        background: rgba(239, 68, 68, 0.15);
        color: #fecaca;
      }

      .status.success {
        background: rgba(34, 197, 94, 0.15);
        color: #bbf7d0;
      }

      .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border-radius: 999px;
        padding: 8px 12px;
        background: rgba(148, 163, 184, 0.12);
      }

      .mono {
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.9rem;
      }

      h1,
      h2,
      p {
        margin-top: 0;
      }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script>
      const { useEffect, useMemo, useRef, useState } = React;

      const STORAGE_KEYS = {
        config: "oauth-spa.config",
        tokens: "oauth-spa.tokens",
        verifier: "oauth-spa.pkce_verifier",
        state: "oauth-spa.oauth_state"
      };

      const defaultConfig = {
        authorizationEndpoint: "https://example.auth.server/authorize",
        tokenEndpoint: "https://example.auth.server/oauth/token",
        clientId: "your-public-client-id",
        redirectUri: window.location.origin + window.location.pathname,
        scope: "openid profile email offline_access",
        apiUrl: "https://api.example.com/userinfo"
      };

      function readJson(key, fallback) {
        try {
          const raw = localStorage.getItem(key);
          return raw ? JSON.parse(raw) : fallback;
        } catch {
          return fallback;
        }
      }

      function writeJson(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
      }

      function base64UrlEncode(bytes) {
        let binary = "";
        for (let i = 0; i < bytes.length; i += 1) {
          binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
      }

      function randomString(byteLength) {
        const bytes = new Uint8Array(byteLength || 32);
        crypto.getRandomValues(bytes);
        return base64UrlEncode(bytes);
      }

      async function sha256(input) {
        const data = new TextEncoder().encode(input);
        const digest = await crypto.subtle.digest("SHA-256", data);
        return new Uint8Array(digest);
      }

      async function createPkcePair() {
        const verifier = randomString(64);
        const challenge = base64UrlEncode(await sha256(verifier));
        return { verifier, challenge };
      }

      function tokensFromResponse(response) {
        const expiresIn = Number(response.expires_in || 0);
        return {
          ...response,
          obtainedAt: Date.now(),
          expiresAt: expiresIn > 0 ? Date.now() + expiresIn * 1000 : null
        };
      }

      function isExpired(tokens) {
        if (!tokens || !tokens.expiresAt) {
          return false;
        }
        return Date.now() >= tokens.expiresAt - 30000;
      }

      async function exchangeCodeForTokens(options) {
        const body = new URLSearchParams({
          grant_type: "authorization_code",
          client_id: options.config.clientId,
          code: options.code,
          redirect_uri: options.config.redirectUri,
          code_verifier: options.verifier
        });

        const response = await fetch(options.config.tokenEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Accept: "application/json"
          },
          body: body.toString()
        });

        if (!response.ok) {
          throw new Error("Token exchange failed: " + response.status + " " + (await response.text()));
        }

        return tokensFromResponse(await response.json());
      }

      async function refreshTokens(options) {
        const body = new URLSearchParams({
          grant_type: "refresh_token",
          client_id: options.config.clientId,
          refresh_token: options.refreshToken
        });

        const response = await fetch(options.config.tokenEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Accept: "application/json"
          },
          body: body.toString()
        });

        if (!response.ok) {
          throw new Error("Refresh failed: " + response.status + " " + (await response.text()));
        }

        const payload = await response.json();
        return tokensFromResponse({
          ...payload,
          refresh_token: payload.refresh_token || options.refreshToken
        });
      }

      function Field(props) {
        return React.createElement(
          "label",
          null,
          React.createElement("div", { className: "muted" }, props.label),
          React.createElement("input", {
            name: props.name,
            value: props.value,
            onChange: props.onChange
          })
        );
      }

      function App() {
        const [config, setConfig] = useState(function () {
          return Object.assign({}, defaultConfig, readJson(STORAGE_KEYS.config, {}));
        });
        const [tokens, setTokens] = useState(function () {
          return readJson(STORAGE_KEYS.tokens, null);
        });
        const [status, setStatus] = useState({
          kind: "info",
          text: "Configure your OAuth provider and sign in."
        });
        const [apiResponse, setApiResponse] = useState("");
        const [busy, setBusy] = useState(false);
        const handledRedirect = useRef(false);

        useEffect(function () {
          writeJson(STORAGE_KEYS.config, config);
        }, [config]);

        useEffect(function () {
          if (tokens) {
            writeJson(STORAGE_KEYS.tokens, tokens);
          } else {
            localStorage.removeItem(STORAGE_KEYS.tokens);
          }
        }, [tokens]);

        useEffect(function () {
          if (handledRedirect.current) {
            return;
          }
          handledRedirect.current = true;

          const params = new URLSearchParams(window.location.search);
          const code = params.get("code");
          const returnedState = params.get("state");
          const error = params.get("error");
          const errorDescription = params.get("error_description");

          if (error) {
            setStatus({
              kind: "error",
              text: errorDescription ? error + ": " + errorDescription : error
            });
            window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
            return;
          }

          if (!code) {
            return;
          }

          const expectedState = localStorage.getItem(STORAGE_KEYS.state);
          const verifier = localStorage.getItem(STORAGE_KEYS.verifier);
          window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);

          if (!returnedState || returnedState !== expectedState || !verifier) {
            setStatus({ kind: "error", text: "OAuth state validation failed." });
            return;
          }

          setBusy(true);
          setStatus({ kind: "info", text: "Exchanging authorization code for tokens..." });

          exchangeCodeForTokens({ code: code, config: config, verifier: verifier })
            .then(function (nextTokens) {
              setTokens(nextTokens);
              setStatus({ kind: "success", text: "Signed in successfully." });
            })
            .catch(function (err) {
              setStatus({ kind: "error", text: err.message });
            })
            .finally(function () {
              localStorage.removeItem(STORAGE_KEYS.state);
              localStorage.removeItem(STORAGE_KEYS.verifier);
              setBusy(false);
            });
        }, [config]);

        const tokenSummary = useMemo(function () {
          if (!tokens) {
            return "Not signed in";
          }
          const expiration = tokens.expiresAt ? new Date(tokens.expiresAt).toLocaleString() : "Unknown";
          return "Access token present" + (tokens.refresh_token ? ", refresh token present" : "") + ", expires: " + expiration;
        }, [tokens]);

        async function beginLogin() {
          setBusy(true);
          setStatus({ kind: "info", text: "Redirecting to the authorization server..." });

          try {
            const pkce = await createPkcePair();
            const state = randomString(24);

            localStorage.setItem(STORAGE_KEYS.verifier, pkce.verifier);
            localStorage.setItem(STORAGE_KEYS.state, state);

            const authUrl = new URL(config.authorizationEndpoint);
            authUrl.searchParams.set("response_type", "code");
            authUrl.searchParams.set("client_id", config.clientId);
            authUrl.searchParams.set("redirect_uri", config.redirectUri);
            authUrl.searchParams.set("scope", config.scope);
            authUrl.searchParams.set("state", state);
            authUrl.searchParams.set("code_challenge", pkce.challenge);
            authUrl.searchParams.set("code_challenge_method", "S256");

            window.location.assign(authUrl.toString());
          } catch (err) {
            setStatus({ kind: "error", text: err.message });
            setBusy(false);
          }
        }

        async function ensureFreshToken() {
          if (!tokens) {
            throw new Error("Sign in before calling the API.");
          }

          if (!isExpired(tokens)) {
            return tokens;
          }

          if (!tokens.refresh_token) {
            throw new Error("Access token expired and no refresh token is available.");
          }

          setStatus({ kind: "info", text: "Refreshing access token..." });
          const refreshed = await refreshTokens({
            config: config,
            refreshToken: tokens.refresh_token
          });
          setTokens(refreshed);
          setStatus({ kind: "success", text: "Access token refreshed." });
          return refreshed;
        }

        async function callApi() {
          setBusy(true);
          setApiResponse("");

          try {
            const currentTokens = await ensureFreshToken();
            const response = await fetch(config.apiUrl, {
              headers: {
                Authorization: "Bearer " + currentTokens.access_token,
                Accept: "application/json"
              }
            });

            const text = await response.text();
            let formatted = text;

            try {
              formatted = JSON.stringify(JSON.parse(text), null, 2);
            } catch {}

            if (!response.ok) {
              throw new Error("API request failed: " + response.status + " " + formatted);
            }

            setApiResponse(formatted);
            setStatus({ kind: "success", text: "Protected API request completed." });
          } catch (err) {
            setStatus({ kind: "error", text: err.message });
          } finally {
            setBusy(false);
          }
        }

        async function refreshNow() {
          if (!tokens || !tokens.refresh_token) {
            setStatus({ kind: "error", text: "No refresh token available." });
            return;
          }

          setBusy(true);
          try {
            const refreshed = await refreshTokens({
              config: config,
              refreshToken: tokens.refresh_token
            });
            setTokens(refreshed);
            setStatus({ kind: "success", text: "Tokens refreshed successfully." });
          } catch (err) {
            setStatus({ kind: "error", text: err.message });
          } finally {
            setBusy(false);
          }
        }

        function signOut() {
          setTokens(null);
          setApiResponse("");
          localStorage.removeItem(STORAGE_KEYS.verifier);
          localStorage.removeItem(STORAGE_KEYS.state);
          setStatus({ kind: "info", text: "Local session cleared." });
        }

        function updateField(event) {
          const name = event.target.name;
          const value = event.target.value;
          setConfig(function (current) {
            return Object.assign({}, current, { [name]: value });
          });
        }

        return React.createElement(
          "div",
          { className: "app" },
          React.createElement(
            "div",
            { className: "card" },
            React.createElement("h1", null, "OAuth 2.0 Authorization Code Flow SPA"),
            React.createElement(
              "p",
              { className: "muted" },
              "React-based mobile web client using Authorization Code + PKCE, fetch() token exchange, and localStorage token persistence."
            ),
            React.createElement("div", { className: "status " + status.kind }, status.text)
          ),
          React.createElement(
            "div",
            { className: "card" },
            React.createElement("h2", null, "OAuth Configuration"),
            React.createElement(
              "div",
              { className: "grid two" },
              React.createElement(Field, {
                label: "Authorization Endpoint",
                name: "authorizationEndpoint",
                value: config.authorizationEndpoint,
                onChange: updateField
              }),
              React.createElement(Field, {
                label: "Token Endpoint",
                name: "tokenEndpoint",
                value: config.tokenEndpoint,
                onChange: updateField
              }),
              React.createElement(Field, {
                label: "Client ID",
                name: "clientId",
                value: config.clientId,
                onChange: updateField
              }),
              React.createElement(Field, {
                label: "Redirect URI",
                name: "redirectUri",
                value: config.redirectUri,
                onChange: updateField
              }),
              React.createElement(Field, {
                label: "Scope",
                name: "scope",
                value: config.scope,
                onChange: updateField
              }),
              React.createElement(Field, {
                label: "Protected API URL",
                name: "apiUrl",
                value: config.apiUrl,
                onChange: updateField
              })
            )
          ),
          React.createElement(
            "div",
            { className: "card" },
            React.createElement("h2", null, "Session"),
            React.createElement("div", { className: "pill mono" }, tokenSummary),
            React.createElement(
              "div",
              { className: "actions", style: { marginTop: "12px" } },
              React.createElement(
                "button",
                { className: "primary", onClick: beginLogin, disabled: busy },
                "Sign In"
              ),
              React.createElement(
                "button",
                {
                  className: "secondary",
                  onClick: refreshNow,
                  disabled: busy || !(tokens && tokens.refresh_token)
                },
                "Refresh Token"
              ),
              React.createElement(
                "button",
                {
                  className: "secondary",
                  onClick: callApi,
                  disabled: busy || !(tokens && tokens.access_token)
                },
                "Call API"
              ),
              React.createElement(
                "button",
                { className: "danger", onClick: signOut, disabled: busy },
                "Sign Out"
              )
            )
          ),
          React.createElement(
            "div",
            { className: "card" },
            React.createElement("h2", null, "Stored Tokens"),
            React.createElement("pre", { className: "mono" }, tokens ? JSON.stringify(tokens, null, 2) : "null")
          ),
          React.createElement(
            "div",
            { className: "card" },
            React.createElement("h2", null, "API Response"),
            React.createElement("pre", { className: "mono" }, apiResponse || "No API response yet.")
          )
        );
      }

      ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
    </script>
  </body>
</html>