import React, { createContext, useContext, useState, useCallback } from "react";
import { startLogin, getLogoutUrl, decodeIdToken } from "./oidcService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = sessionStorage.getItem("oidc_user");
    return stored ? JSON.parse(stored) : null;
  });

  const [tokens, setTokens] = useState(() => {
    const stored = sessionStorage.getItem("oidc_tokens");
    return stored ? JSON.parse(stored) : null;
  });

  const login = useCallback(() => {
    startLogin();
  }, []);

  const setAuthenticated = useCallback((tokenData) => {
    const profile = decodeIdToken(tokenData.id_token);
    setTokens(tokenData);
    setUser(profile);
    sessionStorage.setItem("oidc_tokens", JSON.stringify(tokenData));
    sessionStorage.setItem("oidc_user", JSON.stringify(profile));
  }, []);

  const logout = useCallback(async () => {
    const idToken = tokens?.id_token;
    setUser(null);
    setTokens(null);
    sessionStorage.removeItem("oidc_tokens");
    sessionStorage.removeItem("oidc_user");

    const logoutUrl = await getLogoutUrl(idToken);
    if (logoutUrl) {
      window.location.href = logoutUrl;
    }
  }, [tokens]);

  return (
    <AuthContext.Provider value={{ user, tokens, login, logout, setAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
