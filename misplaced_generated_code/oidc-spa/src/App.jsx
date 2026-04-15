import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  buildAuthorizationUrl,
  clearSession,
  decodeIdTokenPayload,
  getConfig,
  loadSession,
  persistSession,
} from "./oidc.js";

export default function App() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const initial = useMemo(() => loadSession(), []);
  const [tokens, setTokens] = useState(initial.tokens);
  const [profile, setProfile] = useState(initial.profile);

  useEffect(() => {
    if (!tokens?.id_token || profile) return;
    const p = decodeIdTokenPayload(tokens.id_token);
    if (p) {
      persistSession(tokens, p);
      setProfile(p);
    }
  }, [tokens, profile]);

  async function login() {
    setError(null);
    try {
      getConfig();
      const url = await buildAuthorizationUrl();
      window.location.assign(url);
    } catch (e) {
      setError(e.message);
    }
  }

  function logout() {
    clearSession();
    setTokens(null);
    setProfile(null);
    navigate("/", { replace: true });
  }

  if (tokens?.id_token && profile) {
    return (
      <main>
        <h1>Signed in</h1>
        <p>
          <button type="button" onClick={logout}>
            Sign out
          </button>
        </p>
        <h2>Profile (from id_token)</h2>
        <pre>{JSON.stringify(profile, null, 2)}</pre>
      </main>
    );
  }

  if (tokens?.id_token && !profile) {
    return (
      <main>
        <p>Loading profile…</p>
      </main>
    );
  }

  return (
    <main>
      <h1>OIDC SPA</h1>
      {error && <p className="error">{error}</p>}
      <p>
        <button type="button" onClick={login}>
          Sign in with OpenID Connect
        </button>
      </p>
    </main>
  );
}
