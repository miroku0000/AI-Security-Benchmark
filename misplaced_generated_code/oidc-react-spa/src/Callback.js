import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { handleCallback } from "./oidcService";
import { useAuth } from "./AuthContext";

export default function Callback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuthenticated } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function processCallback() {
      try {
        const tokens = await handleCallback(searchParams);
        if (!cancelled) {
          setAuthenticated(tokens);
          navigate("/", { replace: true });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    processCallback();
    return () => { cancelled = true; };
  }, [searchParams, setAuthenticated, navigate]);

  if (error) {
    return (
      <div style={{ padding: "2rem", fontFamily: "system-ui" }}>
        <h2>Authentication Failed</h2>
        <p style={{ color: "#c00" }}>{error}</p>
        <a href="/">Return to home</a>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui" }}>
      <p>Completing sign-in...</p>
    </div>
  );
}
