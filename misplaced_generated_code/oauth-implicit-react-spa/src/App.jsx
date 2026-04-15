import { useEffect, useMemo, useState } from "react";
import {
  buildAuthorizeUrl,
  parseImplicitCallbackFragment,
  savePendingState,
  takePendingState,
} from "./oauthImplicit.js";

const DEFAULT_AUTH_ENDPOINT = "https://example-oauth-provider.com/oauth/authorize";
const DEFAULT_CLIENT_ID = "your-client-id";
function initialRedirectUri() {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}${window.location.pathname}`;
}

function randomState() {
  const a = new Uint8Array(16);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

export default function App() {
  const [authorizationEndpoint, setAuthorizationEndpoint] = useState(DEFAULT_AUTH_ENDPOINT);
  const [clientId, setClientId] = useState(DEFAULT_CLIENT_ID);
  const [redirectUri, setRedirectUri] = useState(initialRedirectUri);
  const [scope, setScope] = useState("openid profile");
  const [tokenResult, setTokenResult] = useState(null);
  const [fragmentNote, setFragmentNote] = useState("");

  const redirectUriEffective = useMemo(() => {
    const base =
      redirectUri.trim() ||
      (typeof window !== "undefined" ? `${window.location.origin}${window.location.pathname}` : "");
    return base.replace(/\/$/, "") || base;
  }, [redirectUri]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const { hash } = window.location;
    if (!hash || hash === "#") return;
    const parsed = parseImplicitCallbackFragment(hash);
    if (parsed.error && parsed.error === "invalid_fragment" && !hash.includes("access_token")) {
      return;
    }
    const expected = takePendingState();
    if (parsed.state && expected && parsed.state !== expected) {
      setTokenResult({
        error: "state_mismatch",
        error_description: "Returned state does not match pending state",
      });
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      return;
    }
    if (parsed.error) {
      setTokenResult(parsed);
    } else {
      setTokenResult(parsed);
    }
    setFragmentNote(hash);
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }, []);

  function startLogin() {
    const st = randomState();
    savePendingState(st);
    const url = buildAuthorizeUrl({
      authorizationEndpoint: authorizationEndpoint.trim(),
      clientId: clientId.trim(),
      redirectUri: redirectUriEffective,
      scope: scope.trim() || undefined,
      state: st,
    });
    window.location.assign(url);
  }

  function logoutLocal() {
    setTokenResult(null);
    setFragmentNote("");
  }

  return (
    <div style={{ fontFamily: "system-ui,sans-serif", maxWidth: 640, margin: "2rem auto", padding: 16 }}>
      <h1 style={{ fontSize: "1.25rem" }}>OAuth 2.0 Implicit (response_type=token)</h1>
      <label style={{ display: "block", marginBottom: 8 }}>
        Authorization endpoint
        <input
          style={{ display: "block", width: "100%", marginTop: 4 }}
          value={authorizationEndpoint}
          onChange={(e) => setAuthorizationEndpoint(e.target.value)}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Client ID
        <input
          style={{ display: "block", width: "100%", marginTop: 4 }}
          value={clientId}
          onChange={(e) => setClientId(e.target.value)}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Redirect URI (must match provider registration)
        <input
          style={{ display: "block", width: "100%", marginTop: 4 }}
          value={redirectUri}
          onChange={(e) => setRedirectUri(e.target.value)}
          placeholder={initialRedirectUri()}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Scope
        <input
          style={{ display: "block", width: "100%", marginTop: 4 }}
          value={scope}
          onChange={(e) => setScope(e.target.value)}
        />
      </label>
      <button type="button" onClick={startLogin}>
        Sign in (implicit)
      </button>
      {tokenResult && (
        <section style={{ marginTop: 24 }}>
          <h2 style={{ fontSize: "1rem" }}>Callback result</h2>
          {tokenResult.error ? (
            <pre style={{ background: "#f6f6f6", padding: 12, overflow: "auto" }}>
              {JSON.stringify(
                {
                  error: tokenResult.error,
                  error_description: tokenResult.error_description,
                  state: tokenResult.state,
                },
                null,
                2
              )}
            </pre>
          ) : (
            <pre style={{ background: "#f6f6f6", padding: 12, overflow: "auto" }}>
              {JSON.stringify(
                {
                  access_token: tokenResult.access_token,
                  token_type: tokenResult.token_type,
                  expires_in: tokenResult.expires_in,
                  expiresAt: tokenResult.expiresAt,
                  state: tokenResult.state,
                },
                null,
                2
              )}
            </pre>
          )}
          {fragmentNote ? (
            <p style={{ fontSize: "0.85rem", color: "#444" }}>
              Parsed fragment was cleared from the URL after reading (original had access_token in #).
            </p>
          ) : null}
          <button type="button" style={{ marginTop: 8 }} onClick={logoutLocal}>
            Clear
          </button>
        </section>
      )}
    </div>
  );
}
