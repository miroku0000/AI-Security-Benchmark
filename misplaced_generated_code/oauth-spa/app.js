import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

const STORAGE_KEYS = {
  accessToken: "oauth_access_token",
  refreshToken: "oauth_refresh_token",
  expiresAt: "oauth_expires_at",
  tokenType: "oauth_token_type",
};

const SESSION_KEYS = {
  state: "oauth_pkce_state",
  codeVerifier: "oauth_code_verifier",
};

function randomUrlSafeString(length) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  let out = "";
  for (let i = 0; i < length; i++) out += alphabet[bytes[i] % alphabet.length];
  return out;
}

async function sha256Base64Url(input) {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = new Uint8Array(digest);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  const b64 = btoa(binary);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function parseQuery(search) {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  return Object.fromEntries(params.entries());
}

function buildAuthorizeUrl(config, { state, codeChallenge }) {
  const u = new URL(config.authorizationEndpoint);
  u.searchParams.set("response_type", "code");
  u.searchParams.set("client_id", config.clientId);
  u.searchParams.set("redirect_uri", config.redirectUri);
  u.searchParams.set("scope", config.scope);
  u.searchParams.set("state", state);
  u.searchParams.set("code_challenge", codeChallenge);
  u.searchParams.set("code_challenge_method", "S256");
  return u.toString();
}

async function exchangeCodeForTokens(config, code, codeVerifier) {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: config.redirectUri,
    client_id: config.clientId,
    code_verifier: codeVerifier,
  });
  if (config.clientSecret) {
    body.set("client_secret", config.clientSecret);
  }
  const res = await fetch(config.tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
    body: body.toString(),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`Token exchange failed (${res.status}): ${text || res.statusText}`);
  }
  if (!res.ok) {
    const msg = json.error_description || json.error || res.statusText;
    throw new Error(`Token exchange failed (${res.status}): ${msg}`);
  }
  return json;
}

async function refreshAccessToken(config) {
  const refresh = localStorage.getItem(STORAGE_KEYS.refreshToken);
  if (!refresh) throw new Error("No refresh token");
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: refresh,
    client_id: config.clientId,
  });
  if (config.clientSecret) body.set("client_secret", config.clientSecret);
  const res = await fetch(config.tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
    body: body.toString(),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`Refresh failed (${res.status}): ${text || res.statusText}`);
  }
  if (!res.ok) {
    const msg = json.error_description || json.error || res.statusText;
    throw new Error(`Refresh failed (${res.status}): ${msg}`);
  }
  return json;
}

function persistTokenResponse(json) {
  if (json.access_token) localStorage.setItem(STORAGE_KEYS.accessToken, json.access_token);
  if (json.refresh_token) localStorage.setItem(STORAGE_KEYS.refreshToken, json.refresh_token);
  if (json.token_type) localStorage.setItem(STORAGE_KEYS.tokenType, json.token_type);
  if (typeof json.expires_in === "number" && Number.isFinite(json.expires_in)) {
    const expiresAt = Date.now() + json.expires_in * 1000;
    localStorage.setItem(STORAGE_KEYS.expiresAt, String(expiresAt));
  }
}

function clearStoredTokens() {
  Object.values(STORAGE_KEYS).forEach((k) => localStorage.removeItem(k));
}

function getStoredAccessToken() {
  return localStorage.getItem(STORAGE_KEYS.accessToken);
}

function getAuthHeaderValue() {
  const token = getStoredAccessToken();
  if (!token) return null;
  const type = localStorage.getItem(STORAGE_KEYS.tokenType) || "Bearer";
  return `${type} ${token}`;
}

function defaultConfig() {
  return {
    authorizationEndpoint: "",
    tokenEndpoint: "",
    clientId: "",
    clientSecret: "",
    redirectUri: `${window.location.origin}${window.location.pathname}`,
    scope: "openid profile email",
    apiUrl: "",
  };
}

function loadConfig() {
  try {
    const raw = localStorage.getItem("oauth_app_config");
    if (!raw) return defaultConfig();
    return { ...defaultConfig(), ...JSON.parse(raw) };
  } catch {
    return defaultConfig();
  }
}

function saveConfig(config) {
  localStorage.setItem("oauth_app_config", JSON.stringify(config));
}

function App() {
  const [config, setConfig] = useState(loadConfig);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tokenPreview, setTokenPreview] = useState(null);
  const [apiBody, setApiBody] = useState("");
  const [authTick, setAuthTick] = useState(0);

  const hasToken = useMemo(() => !!getStoredAccessToken(), [authTick, tokenPreview]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { search, pathname, hash } = window.location;
      const fromHash = hash && hash.length > 1 ? parseQuery(hash.slice(1)) : {};
      const fromSearch = parseQuery(search);
      const code = fromSearch.code || fromHash.code;
      const state = fromSearch.state || fromHash.state;
      const err = fromSearch.error || fromHash.error;
      if (err) {
        setError(`${err}: ${fromSearch.error_description || fromHash.error_description || ""}`);
        window.history.replaceState({}, document.title, pathname);
        return;
      }
      if (!code || !state) return;
      const savedState = sessionStorage.getItem(SESSION_KEYS.state);
      const codeVerifier = sessionStorage.getItem(SESSION_KEYS.codeVerifier);
      if (!savedState || state !== savedState || !codeVerifier) {
        setError("Invalid OAuth state; try signing in again.");
        window.history.replaceState({}, document.title, pathname);
        return;
      }
      setBusy(true);
      setError("");
      try {
        const cfg = loadConfig();
        const json = await exchangeCodeForTokens(cfg, code, codeVerifier);
        if (cancelled) return;
        persistTokenResponse(json);
        setTokenPreview(json);
        setAuthTick((t) => t + 1);
        sessionStorage.removeItem(SESSION_KEYS.state);
        sessionStorage.removeItem(SESSION_KEYS.codeVerifier);
      } catch (e) {
        if (!cancelled) setError(e.message || String(e));
      } finally {
        if (!cancelled) setBusy(false);
        window.history.replaceState({}, document.title, pathname);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const updateField = useCallback((key, value) => {
    setConfig((c) => {
      const next = { ...c, [key]: value };
      saveConfig(next);
      return next;
    });
  }, []);

  const onLogin = useCallback(async () => {
    setError("");
    setBusy(true);
    try {
      const state = randomUrlSafeString(32);
      const codeVerifier = randomUrlSafeString(64);
      const codeChallenge = await sha256Base64Url(codeVerifier);
      sessionStorage.setItem(SESSION_KEYS.state, state);
      sessionStorage.setItem(SESSION_KEYS.codeVerifier, codeVerifier);
      const url = buildAuthorizeUrl(config, { state, codeChallenge });
      window.location.assign(url);
    } catch (e) {
      setError(e.message || String(e));
      setBusy(false);
    }
  }, [config]);

  const onLogout = useCallback(() => {
    clearStoredTokens();
    setTokenPreview(null);
    setApiBody("");
    setAuthTick((t) => t + 1);
  }, []);

  const onRefresh = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const json = await refreshAccessToken(loadConfig());
      persistTokenResponse(json);
      setTokenPreview(json);
      setAuthTick((t) => t + 1);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const onApiFetch = useCallback(async () => {
    setBusy(true);
    setError("");
    setApiBody("");
    try {
      const cfg = loadConfig();
      if (!cfg.apiUrl) throw new Error("Set API URL first");
      const auth = getAuthHeaderValue();
      if (!auth) throw new Error("No access token");
      const res = await fetch(cfg.apiUrl, {
        headers: { Authorization: auth, Accept: "application/json" },
      });
      const text = await res.text();
      setApiBody(`${res.status} ${res.statusText}\n\n${text}`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const statusLine = useMemo(() => {
    const exp = localStorage.getItem(STORAGE_KEYS.expiresAt);
    if (!exp) return hasToken ? "Signed in (no expiry recorded)" : "Not signed in";
    const t = Number(exp);
    if (!Number.isFinite(t)) return hasToken ? "Signed in" : "Not signed in";
    const left = Math.max(0, Math.floor((t - Date.now()) / 1000));
    return hasToken ? `Signed in · access token expires in ~${left}s` : "Not signed in";
  }, [hasToken, tokenPreview]);

  return React.createElement(
    "div",
    { className: "card" },
    React.createElement("h1", { style: { fontSize: "22px", marginTop: 0 } }, "OAuth 2.0 (PKCE)"),
    React.createElement("p", { className: "muted" }, statusLine),
    React.createElement(
      "div",
      null,
      React.createElement("label", null, "Authorization endpoint"),
      React.createElement("input", {
        value: config.authorizationEndpoint,
        onChange: (e) => updateField("authorizationEndpoint", e.target.value),
        placeholder: "https://issuer/oauth2/authorize",
        autoComplete: "off",
        autoCorrect: "off",
      }),
      React.createElement("label", null, "Token endpoint"),
      React.createElement("input", {
        value: config.tokenEndpoint,
        onChange: (e) => updateField("tokenEndpoint", e.target.value),
        placeholder: "https://issuer/oauth2/token",
      }),
      React.createElement("label", null, "Client ID"),
      React.createElement("input", {
        value: config.clientId,
        onChange: (e) => updateField("clientId", e.target.value),
        placeholder: "your-client-id",
      }),
      React.createElement("label", null, "Client secret (optional; confidential clients only)"),
      React.createElement("input", {
        type: "password",
        value: config.clientSecret,
        onChange: (e) => updateField("clientSecret", e.target.value),
        placeholder: "leave empty for public / PKCE-only",
      }),
      React.createElement("label", null, "Redirect URI (must match IdP registration)"),
      React.createElement("input", {
        value: config.redirectUri,
        onChange: (e) => updateField("redirectUri", e.target.value),
      }),
      React.createElement("label", null, "Scope"),
      React.createElement("input", {
        value: config.scope,
        onChange: (e) => updateField("scope", e.target.value),
      }),
      React.createElement("label", null, "API URL (demo GET with Authorization header)"),
      React.createElement("input", {
        value: config.apiUrl,
        onChange: (e) => updateField("apiUrl", e.target.value),
        placeholder: "https://api.example.com/v1/me",
      })
    ),
    error ? React.createElement("div", { className: "err" }, error) : null,
    React.createElement(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "10px", marginTop: "16px" } },
      React.createElement(
        "button",
        { type: "button", onClick: onLogin, disabled: busy },
        busy ? "Working…" : "Sign in"
      ),
      React.createElement(
        "button",
        {
          type: "button",
          onClick: onRefresh,
          disabled: busy || !localStorage.getItem(STORAGE_KEYS.refreshToken),
          style: { background: "#374151" },
        },
        "Refresh access token"
      ),
      React.createElement(
        "button",
        { type: "button", onClick: onApiFetch, disabled: busy || !hasToken, style: { background: "#0d9488" } },
        "Call API (fetch)"
      ),
      React.createElement("button", { type: "button", onClick: onLogout, disabled: busy, style: { background: "#b45309" } }, "Sign out & clear tokens")
    ),
    tokenPreview
      ? React.createElement(
          "div",
          { style: { marginTop: "16px" } },
          React.createElement("div", { className: "muted" }, "Last token response"),
          React.createElement("pre", null, JSON.stringify(tokenPreview, null, 2))
        )
      : null,
    apiBody
      ? React.createElement(
          "div",
          { style: { marginTop: "16px" } },
          React.createElement("div", { className: "muted" }, "API response"),
          React.createElement("pre", null, apiBody)
        )
      : null
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
