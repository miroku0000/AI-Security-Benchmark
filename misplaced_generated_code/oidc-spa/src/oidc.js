const STORAGE_STATE = "oidc_state";
const STORAGE_NONCE = "oidc_nonce";
const STORAGE_VERIFIER = "oidc_verifier";
const STORAGE_TOKENS = "oidc_tokens";
const STORAGE_PROFILE = "oidc_profile";

function randomString(len = 64) {
  const alphabet =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const bytes = new Uint8Array(len);
  crypto.getRandomValues(bytes);
  let s = "";
  for (let i = 0; i < len; i++) s += alphabet[bytes[i] % alphabet.length];
  return s;
}

async function sha256Base64Url(plain) {
  const data = new TextEncoder().encode(plain);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const b64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function getConfig() {
  const issuer = import.meta.env.VITE_OIDC_ISSUER?.replace(/\/+$/, "");
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID;
  const redirectUri = import.meta.env.VITE_OIDC_REDIRECT_URI;
  if (!issuer || !clientId || !redirectUri) {
    throw new Error(
      "Set VITE_OIDC_ISSUER, VITE_OIDC_CLIENT_ID, VITE_OIDC_REDIRECT_URI in .env"
    );
  }
  return { issuer, clientId, redirectUri };
}

let discoveryCache = null;

export async function discover() {
  if (discoveryCache) return discoveryCache;
  const { issuer } = getConfig();
  const res = await fetch(
    `${issuer}/.well-known/openid-configuration`
  );
  if (!res.ok) throw new Error(`OpenID discovery failed: ${res.status}`);
  discoveryCache = await res.json();
  return discoveryCache;
}

export async function buildAuthorizationUrl() {
  const { clientId, redirectUri } = getConfig();
  const d = await discover();
  const state = randomString(32);
  const nonce = randomString(32);
  const verifier = randomString(64);
  const challenge = await sha256Base64Url(verifier);
  sessionStorage.setItem(STORAGE_STATE, state);
  sessionStorage.setItem(STORAGE_NONCE, nonce);
  sessionStorage.setItem(STORAGE_VERIFIER, verifier);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: "openid profile email",
    state,
    nonce,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  return `${d.authorization_endpoint}?${params.toString()}`;
}

export function readCallbackParams() {
  const search = new URLSearchParams(window.location.search);
  return {
    code: search.get("code"),
    state: search.get("state"),
    error: search.get("error"),
    errorDescription: search.get("error_description"),
  };
}

export async function exchangeCodeForTokens(code) {
  const { clientId, redirectUri } = getConfig();
  const verifier = sessionStorage.getItem(STORAGE_VERIFIER);
  if (!verifier) throw new Error("Missing PKCE verifier");
  const d = await discover();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    client_id: clientId,
    code_verifier: verifier,
  });
  const res = await fetch(d.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = json.error_description || json.error || res.statusText;
    throw new Error(msg);
  }
  sessionStorage.removeItem(STORAGE_VERIFIER);
  sessionStorage.removeItem(STORAGE_STATE);
  sessionStorage.removeItem(STORAGE_NONCE);
  return json;
}

export function decodeIdTokenPayload(idToken) {
  if (!idToken || typeof idToken !== "string") return null;
  const parts = idToken.split(".");
  if (parts.length < 2) return null;
  const payload = parts[1];
  const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
  const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(json);
}

export function persistSession(tokens, profile) {
  sessionStorage.setItem(STORAGE_TOKENS, JSON.stringify(tokens));
  sessionStorage.setItem(STORAGE_PROFILE, JSON.stringify(profile));
}

export function loadSession() {
  try {
    const t = sessionStorage.getItem(STORAGE_TOKENS);
    const p = sessionStorage.getItem(STORAGE_PROFILE);
    if (!t) return { tokens: null, profile: null };
    return {
      tokens: JSON.parse(t),
      profile: p ? JSON.parse(p) : null,
    };
  } catch {
    return { tokens: null, profile: null };
  }
}

export function clearSession() {
  sessionStorage.removeItem(STORAGE_TOKENS);
  sessionStorage.removeItem(STORAGE_PROFILE);
}

export function getExpectedState() {
  return sessionStorage.getItem(STORAGE_STATE);
}
