import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { oauthConfig } from '../config/oauth';
import {
  clearTokens,
  loadTokens,
  saveTokens,
  type StoredTokens,
} from './tokenStorage';
import {
  exchangeAuthorizationCode,
  getValidAccessToken,
  refreshTokensIfNeeded,
} from './oauthService';

WebBrowser.maybeCompleteAuthSession();

type AuthState = {
  tokens: StoredTokens | null;
  isLoading: boolean;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [tokens, setTokens] = useState<StoredTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const redirectUri = AuthSession.makeRedirectUri({
    scheme: 'mobileoauthapp',
    path: oauthConfig.redirectPath,
  });

  const discovery = useMemo(
    () => ({
      authorizationEndpoint: oauthConfig.authorizationEndpoint,
      tokenEndpoint: oauthConfig.tokenEndpoint,
    }),
    []
  );

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: oauthConfig.clientId,
      scopes: [...oauthConfig.scopes],
      redirectUri,
      responseType: AuthSession.ResponseType.Code,
      usePKCE: true,
    },
    discovery
  );

  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleRefresh = useCallback((stored: StoredTokens | null) => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
    if (!stored?.refreshToken || stored.expiresAt == null) return;

    const msUntil = Math.max(
      1000,
      (stored.expiresAt - 60 - Math.floor(Date.now() / 1000)) * 1000
    );

    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        const next = await refreshTokensIfNeeded();
        if (next) {
          setTokens(next);
          scheduleRefresh(next);
        }
      } catch {
        setTokens(null);
      }
    }, msUntil);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const stored = await loadTokens();
        if (stored) {
          try {
            const next = await refreshTokensIfNeeded();
            setTokens(next ?? stored);
            scheduleRefresh(next ?? stored);
          } catch {
            setTokens(stored);
            scheduleRefresh(stored);
          }
        }
      } finally {
        setIsLoading(false);
      }
    })();
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [scheduleRefresh]);

  useEffect(() => {
    if (response?.type !== 'success') return;
    const code = response.params.code;
    const codeVerifier = request?.codeVerifier;
    if (!code || !codeVerifier) {
      setError('Missing authorization code or PKCE verifier');
      return;
    }

    (async () => {
      try {
        setError(null);
        const next = await exchangeAuthorizationCode({
          code,
          redirectUri,
          codeVerifier,
        });
        await saveTokens(next);
        setTokens(next);
        scheduleRefresh(next);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Sign-in failed');
      }
    })();
  }, [response, request, redirectUri, scheduleRefresh]);

  const signIn = useCallback(async () => {
    setError(null);
    if (!request) {
      setError('OAuth request not ready');
      return;
    }
    await promptAsync();
  }, [request, promptAsync]);

  const signOut = useCallback(async () => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
    await clearTokens();
    setTokens(null);
  }, []);

  const getAccessToken = useCallback(async () => {
    const t = await getValidAccessToken();
    if (t) {
      const stored = await loadTokens();
      if (stored) setTokens(stored);
    }
    return t;
  }, []);

  const value = useMemo(
    () => ({
      tokens,
      isLoading,
      error,
      signIn,
      signOut,
      getAccessToken,
    }),
    [tokens, isLoading, error, signIn, signOut, getAccessToken]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
