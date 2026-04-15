import oidcConfig from "./oidcConfig";
import { generateCodeVerifier, generateCodeChallenge } from "./pkce";

let discoveryCache = null;

// Fetch OIDC discovery document from the provider's well-known endpoint.
async function fetchDiscovery() {
  if (discoveryCache) return discoveryCache;

  const url = `${oidcConfig.authority}/.well-known/openid-configuration`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch OIDC discovery: ${response.status}`);
  }
  discoveryCache = await response.json();
  return discoveryCache;
}

// Generate a cryptographically random state parameter to prevent CSRF.
function generateState() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Generate a nonce for id_token replay protection.
function generateNonce() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Initiate the authorization code flow with PKCE by redirecting the browser.
export async function startLogin() {
  const discovery = await fetchDiscovery();
  const state = generateState();
  const nonce = generateNonce();
  const codeVerifier = await generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Store PKCE verifier, state, and nonce in sessionStorage (cleared on tab close).
  sessionStorage.setItem("oidc_code_verifier", codeVerifier);
  sessionStorage.setItem("oidc_state", state);
  sessionStorage.setItem("oidc_nonce", nonce);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: oidcConfig.clientId,
    redirect_uri: oidcConfig.redirectUri,
    scope: oidcConfig.scopes,
    state: state,
    nonce: nonce,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  window.location.href = `${discovery.authorization_endpoint}?${params.toString()}`;
}

// Handle the callback: validate state, exchange code for tokens using PKCE.
export async function handleCallback(searchParams) {
  const code = searchParams.get("code");
  const returnedState = searchParams.get("state");
  const error = searchParams.get("error");

  if (error) {
    const description = searchParams.get("error_description") || error;
    throw new Error(`Authorization error: ${description}`);
  }

  if (!code) {
    throw new Error("No authorization code in callback");
  }

  // Validate state to prevent CSRF attacks.
  const savedState = sessionStorage.getItem("oidc_state");
  if (!savedState || returnedState !== savedState) {
    sessionStorage.removeItem("oidc_state");
    sessionStorage.removeItem("oidc_code_verifier");
    sessionStorage.removeItem("oidc_nonce");
    throw new Error("State mismatch — possible CSRF attack");
  }

  const codeVerifier = sessionStorage.getItem("oidc_code_verifier");
  if (!codeVerifier) {
    throw new Error("Missing PKCE code verifier");
  }

  // Clean up stored values.
  sessionStorage.removeItem("oidc_state");
  sessionStorage.removeItem("oidc_code_verifier");

  const discovery = await fetchDiscovery();

  // Exchange authorization code for tokens at the token endpoint.
  const tokenResponse = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code: code,
      redirect_uri: oidcConfig.redirectUri,
      client_id: oidcConfig.clientId,
      code_verifier: codeVerifier,
    }),
  });

  if (!tokenResponse.ok) {
    const body = await tokenResponse.text();
    throw new Error(`Token exchange failed: ${tokenResponse.status} ${body}`);
  }

  const tokens = await tokenResponse.json();

  // Validate the nonce in the id_token to prevent replay attacks.
  const savedNonce = sessionStorage.getItem("oidc_nonce");
  const idPayload = decodeIdToken(tokens.id_token);
  if (savedNonce && idPayload.nonce !== savedNonce) {
    sessionStorage.removeItem("oidc_nonce");
    throw new Error("Nonce mismatch — possible replay attack");
  }
  sessionStorage.removeItem("oidc_nonce");

  return tokens;
}

// Decode id_token JWT payload (signature verification should be done server-side
// or via JWKS in production; PKCE mitigates token injection for public clients).
export function decodeIdToken(idToken) {
  if (!idToken) return null;
  const parts = idToken.split(".");
  if (parts.length !== 3) {
    throw new Error("Invalid id_token format");
  }
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const decoded = atob(payload);
  return JSON.parse(decoded);
}

// Build the end-session (logout) URL per OIDC RP-Initiated Logout spec.
export async function getLogoutUrl(idToken) {
  const discovery = await fetchDiscovery();
  if (!discovery.end_session_endpoint) return null;

  const params = new URLSearchParams({
    id_token_hint: idToken,
    post_logout_redirect_uri: oidcConfig.postLogoutRedirectUri,
  });
  return `${discovery.end_session_endpoint}?${params.toString()}`;
}
