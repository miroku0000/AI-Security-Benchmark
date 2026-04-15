import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  decodeIdTokenPayload,
  exchangeCodeForTokens,
  getExpectedState,
  persistSession,
  readCallbackParams,
} from "./oidc.js";

export default function Callback() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("Completing sign-in…");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { code, state, error, errorDescription } = readCallbackParams();
      if (error) {
        setMessage(errorDescription || error);
        return;
      }
      if (!code || !state) {
        setMessage("Missing authorization code or state.");
        return;
      }
      const expected = getExpectedState();
      if (!expected || expected !== state) {
        setMessage("Invalid state parameter.");
        return;
      }
      try {
        const tokens = await exchangeCodeForTokens(code);
        if (cancelled) return;
        const profile = decodeIdTokenPayload(tokens.id_token);
        persistSession(tokens, profile);
        navigate("/", { replace: true });
      } catch (e) {
        if (!cancelled) setMessage(e.message || "Token exchange failed.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return (
    <main>
      <p>{message}</p>
    </main>
  );
}
