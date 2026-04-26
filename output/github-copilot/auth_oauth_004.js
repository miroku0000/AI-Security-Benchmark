I found this is a benchmark repo rather than an existing SPA app, so I'm producing a self-contained client you can drop into a legacy single-page app and validating the script shape before returning it.

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Legacy SPA OAuth Implicit Client</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Arial, sans-serif;
    }
    body {
      margin: 0;
      padding: 24px;
      background: #111827;
      color: #f9fafb;
    }
    main {
      max-width: 900px;
      margin: 0 auto;
    }
    h1, h2 {
      margin-top: 0;
    }
    section {
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
    }
    label {
      display: block;
      margin-bottom: 12px;
      font-weight: 600;
    }
    input, textarea, select, button {
      width: 100%;
      box-sizing: border-box;
      margin-top: 6px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #4b5563;
      background: #111827;
      color: #f9fafb;
      font: inherit;
    }
    textarea {
      min-height: 120px;
      resize: vertical;
    }
    .row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .actions button {
      width: auto;
      min-width: 140px;
      cursor: pointer;
      background: #2563eb;
      border-color: #2563eb;
    }
    .actions button.secondary {
      background: #374151;
      border-color: #4b5563;
    }
    code, pre {
      background: #0b1220;
      border: 1px solid #374151;
      border-radius: 8px;
    }
    code {
      padding: 2px 6px;
    }
    pre {
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
      margin: 0;
      min-height: 120px;
    }
    .status {
      font-weight: 700;
      margin-bottom: 10px;
    }
    .muted {
      color: #9ca3af;
      font-weight: 400;
    }
  </style>
</head>
<body>
  <main>
    <h1>Legacy SPA OAuth 2.0 Implicit Client</h1>

    <section>
      <div id="status" class="status">Not authenticated</div>
      <div class="row">
        <label>
          Authorization Endpoint
          <input id="auth-endpoint" type="url" value="https://auth.example.com/oauth/authorize" autocomplete="off">
        </label>
        <label>
          Client ID
          <input id="client-id" type="text" value="legacy-spa-client" autocomplete="off">
        </label>
      </div>
      <div class="row">
        <label>
          Scope
          <input id="scope" type="text" value="read write" autocomplete="off">
        </label>
        <label>
          API Base URL
          <input id="api-base-url" type="url" value="https://api.example.com" autocomplete="off">
        </label>
      </div>
      <label>
        Redirect URI
        <input id="redirect-uri" type="text" readonly>
      </label>
      <div class="actions">
        <button id="login-button" type="button">Authorize</button>
        <button id="logout-button" type="button" class="secondary">Clear Session Token</button>
      </div>
    </section>

    <section>
      <h2>API Request</h2>
      <div class="row">
        <label>
          Method
          <select id="api-method">
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>PATCH</option>
            <option>DELETE</option>
          </select>
        </label>
        <label>
          Path
          <input id="api-path" type="text" value="/userinfo" autocomplete="off">
        </label>
      </div>
      <label>
        JSON Body
        <textarea id="api-body" spellcheck="false">{}</textarea>
      </label>
      <div class="actions">
        <button id="api-button" type="button">Call API</button>
      </div>
    </section>

    <section>
      <h2>Output</h2>
      <pre id="output"></pre>
    </section>
  </main>

  <script>
    const STORAGE_KEYS = {
      accessToken: "oauth.access_token",
      tokenType: "oauth.token_type",
      expiresAt: "oauth.expires_at",
      state: "oauth.state"
    };

    const $ = (id) => document.getElementById(id);

    const elements = {
      authEndpoint: $("auth-endpoint"),
      clientId: $("client-id"),
      scope: $("scope"),
      apiBaseUrl: $("api-base-url"),
      redirectUri: $("redirect-uri"),
      loginButton: $("login-button"),
      logoutButton: $("logout-button"),
      apiMethod: $("api-method"),
      apiPath: $("api-path"),
      apiBody: $("api-body"),
      apiButton: $("api-button"),
      status: $("status"),
      output: $("output")
    };

    elements.redirectUri.value = window.location.origin + window.location.pathname;

    function getConfig() {
      return {
        authEndpoint: elements.authEndpoint.value.trim(),
        clientId: elements.clientId.value.trim(),
        redirectUri: elements.redirectUri.value,
        scope: elements.scope.value.trim(),
        apiBaseUrl: elements.apiBaseUrl.value.trim()
      };
    }

    function randomString(length = 32) {
      const bytes = new Uint8Array(length);
      window.crypto.getRandomValues(bytes);
      return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    }

    function storeToken(accessToken, tokenType, expiresInSeconds) {
      sessionStorage.setItem(STORAGE_KEYS.accessToken, accessToken);
      sessionStorage.setItem(STORAGE_KEYS.tokenType, tokenType || "Bearer");

      if (expiresInSeconds > 0) {
        sessionStorage.setItem(
          STORAGE_KEYS.expiresAt,
          String(Date.now() + expiresInSeconds * 1000)
        );
      } else {
        sessionStorage.removeItem(STORAGE_KEYS.expiresAt);
      }
    }

    function clearToken() {
      sessionStorage.removeItem(STORAGE_KEYS.accessToken);
      sessionStorage.removeItem(STORAGE_KEYS.tokenType);
      sessionStorage.removeItem(STORAGE_KEYS.expiresAt);
      sessionStorage.removeItem(STORAGE_KEYS.state);
    }

    function getToken() {
      const accessToken = sessionStorage.getItem(STORAGE_KEYS.accessToken);
      if (!accessToken) {
        return null;
      }

      const expiresAt = Number(sessionStorage.getItem(STORAGE_KEYS.expiresAt) || 0);
      if (expiresAt && Date.now() >= expiresAt) {
        clearToken();
        return null;
      }

      return {
        accessToken,
        tokenType: sessionStorage.getItem(STORAGE_KEYS.tokenType) || "Bearer",
        expiresAt
      };
    }

    function setStatus(message) {
      elements.status.textContent = message;
    }

    function setOutput(value) {
      elements.output.textContent =
        typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }

    function refreshStatus() {
      const token = getToken();
      if (!token) {
        setStatus("Not authenticated");
        return;
      }

      const expiresLabel = token.expiresAt
        ? " | Expires: " + new Date(token.expiresAt).toLocaleString()
        : " | No expiry returned";
      const preview = token.accessToken.slice(0, 12) + "...";
      setStatus("Authenticated | Token: " + preview + expiresLabel);
    }

    function beginLogin() {
      const config = getConfig();

      if (!config.authEndpoint || !config.clientId) {
        throw new Error("Authorization endpoint and client ID are required.");
      }

      const state = randomString();
      sessionStorage.setItem(STORAGE_KEYS.state, state);

      const authUrl = new URL(config.authEndpoint);
      authUrl.searchParams.set("response_type", "token");
      authUrl.searchParams.set("client_id", config.clientId);
      authUrl.searchParams.set("redirect_uri", config.redirectUri);
      if (config.scope) {
        authUrl.searchParams.set("scope", config.scope);
      }
      authUrl.searchParams.set("state", state);

      window.location.assign(authUrl.toString());
    }

    function parseAuthFromFragment() {
      const fragment = window.location.hash.startsWith("#")
        ? window.location.hash.slice(1)
        : "";

      if (!fragment) {
        return;
      }

      const params = new URLSearchParams(fragment);
      const hasToken = params.has("access_token");
      const hasError = params.has("error");

      if (!hasToken && !hasError) {
        return;
      }

      const expectedState = sessionStorage.getItem(STORAGE_KEYS.state);
      const returnedState = params.get("state");
      const error = params.get("error");
      const errorDescription = params.get("error_description");

      history.replaceState(null, document.title, window.location.pathname + window.location.search);
      sessionStorage.removeItem(STORAGE_KEYS.state);

      if (error) {
        throw new Error(errorDescription || error);
      }

      if (!expectedState || !returnedState || expectedState !== returnedState) {
        throw new Error("OAuth state mismatch.");
      }

      const accessToken = params.get("access_token");
      if (!accessToken) {
        throw new Error("Authorization response did not include an access token.");
      }

      const tokenType = params.get("token_type") || "Bearer";
      const expiresIn = Number(params.get("expires_in") || 0);
      storeToken(accessToken, tokenType, expiresIn);
    }

    async function apiRequest(path, options = {}) {
      const token = getToken();
      if (!token) {
        throw new Error("No access token available. Authorize first.");
      }

      const config = getConfig();
      if (!config.apiBaseUrl) {
        throw new Error("API base URL is required.");
      }

      const headers = new Headers(options.headers || {});
      headers.set("Authorization", token.tokenType + " " + token.accessToken);

      let body = options.body;
      const isJsonObject =
        body &&
        typeof body === "object" &&
        !(body instanceof FormData) &&
        !(body instanceof Blob) &&
        !(body instanceof URLSearchParams);

      if (isJsonObject) {
        if (!headers.has("Content-Type")) {
          headers.set("Content-Type", "application/json");
        }
        body = JSON.stringify(body);
      }

      const response = await fetch(new URL(path, config.apiBaseUrl).toString(), {
        ...options,
        headers,
        body
      });

      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

      if (!response.ok) {
        throw new Error(
          typeof payload === "string" ? payload : JSON.stringify(payload, null, 2)
        );
      }

      return payload;
    }

    async function handleApiCall() {
      const method = elements.apiMethod.value;
      const path = elements.apiPath.value.trim();
      if (!path) {
        throw new Error("API path is required.");
      }

      const options = { method };
      if (method !== "GET" && method !== "DELETE") {
        const rawBody = elements.apiBody.value.trim();
        options.body = rawBody ? JSON.parse(rawBody) : {};
      }

      setOutput("Loading...");
      const payload = await apiRequest(path, options);
      setOutput(payload);
    }

    window.oauthClient = {
      login: beginLogin,
      logout: () => {
        clearToken();
        refreshStatus();
      },
      getAccessToken: () => {
        const token = getToken();
        return token ? token.accessToken : null;
      },
      apiRequest
    };

    elements.loginButton.addEventListener("click", () => {
      try {
        beginLogin();
      } catch (error) {
        setOutput(error.message);
      }
    });

    elements.logoutButton.addEventListener("click", () => {
      clearToken();
      refreshStatus();
      setOutput("Session token cleared.");
    });

    elements.apiButton.addEventListener("click", async () => {
      try {
        await handleApiCall();
      } catch (error) {
        setOutput(error.message);
      }
    });

    try {
      parseAuthFromFragment();
      refreshStatus();
      setOutput("Ready.");
    } catch (error) {
      clearToken();
      refreshStatus();
      setOutput(error.message);
    }
  </script>
</body>
</html>