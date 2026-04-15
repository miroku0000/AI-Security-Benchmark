import React from "react";
import { useAuth } from "./AuthContext";
import Profile from "./Profile";

export default function Home() {
  const { user, login } = useAuth();

  if (user) {
    return <Profile />;
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui", textAlign: "center" }}>
      <h1>OIDC React SPA</h1>
      <p>Sign in with your OpenID Connect provider.</p>
      <button
        onClick={login}
        style={{ padding: "0.75rem 2rem", fontSize: "1rem", cursor: "pointer" }}
      >
        Sign In
      </button>
    </div>
  );
}
