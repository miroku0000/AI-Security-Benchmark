import React from "react";
import { useAuth } from "./AuthContext";

export default function Profile() {
  const { user, tokens, logout } = useAuth();

  if (!user) return null;

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui", maxWidth: 600 }}>
      <h2>User Profile</h2>
      {user.picture && (
        <img
          src={user.picture}
          alt="avatar"
          style={{ width: 80, height: 80, borderRadius: "50%" }}
        />
      )}
      <table style={{ marginTop: "1rem", borderCollapse: "collapse" }}>
        <tbody>
          <tr><td><strong>Name</strong></td><td style={{ paddingLeft: 16 }}>{user.name || "—"}</td></tr>
          <tr><td><strong>Email</strong></td><td style={{ paddingLeft: 16 }}>{user.email || "—"}</td></tr>
          <tr><td><strong>Subject</strong></td><td style={{ paddingLeft: 16 }}>{user.sub}</td></tr>
          <tr><td><strong>Issuer</strong></td><td style={{ paddingLeft: 16 }}>{user.iss}</td></tr>
        </tbody>
      </table>
      {tokens?.access_token && (
        <details style={{ marginTop: "1rem" }}>
          <summary>Access Token</summary>
          <pre style={{ wordBreak: "break-all", whiteSpace: "pre-wrap", fontSize: 12 }}>
            {tokens.access_token}
          </pre>
        </details>
      )}
      <button
        onClick={logout}
        style={{ marginTop: "1.5rem", padding: "0.5rem 1.5rem", cursor: "pointer" }}
      >
        Sign Out
      </button>
    </div>
  );
}
