import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator, Linking, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as AuthSession from 'expo-auth-session';
import * as Crypto from 'expo-crypto';
import * as WebBrowser from 'expo-web-browser';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
// Mobile apps are PUBLIC clients – they MUST NOT contain a client_secret.
// Anyone can decompile an APK/IPA and extract embedded secrets.
// We use Authorization Code Flow with PKCE (RFC 7636) instead.
// ---------------------------------------------------------------------------
const OAUTH_CONFIG = {
  clientId: 'YOUR_CLIENT_ID',               // public identifier – safe to embed
  // NO client_secret here. Mobile apps must use PKCE, not client credentials.
  authorizationEndpoint: 'https://auth.example.com/authorize',
  tokenEndpoint: 'https://auth.example.com/oauth/token',
  revocationEndpoint: 'https://auth.example.com/oauth/revoke',
  redirectUri: AuthSession.makeRedirectUri({ scheme: 'myapp', path: 'callback' }),
  scopes: ['openid', 'profile', 'email', 'offline_access'],
};

const STORAGE_KEYS = {
  accessToken: '@oauth_access_token',
  refreshToken: '@oauth_refresh_token',
  expiresAt: '@oauth_expires_at',
  idToken: '@oauth_id_token',
};

// Refresh 5 minutes before actual expiry
const REFRESH_BUFFER_MS = 5 * 60 * 1000;

// ---------------------------------------------------------------------------
// PKCE helpers (RFC 7636)
// ---------------------------------------------------------------------------
async function generateCodeVerifier(): Promise<string> {
  const randomBytes = await Crypto.getRandomBytesAsync(32);
  return base64UrlEncode(randomBytes);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const digest = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    verifier,
    { encoding: Crypto.CryptoEncoding.BASE64 },
  );
  return base64UrlFromBase64(digest);
}

function base64UrlEncode(buffer: Uint8Array): string {
  const str = btoa(String.fromCharCode(...buffer));
  return base64UrlFromBase64(str);
}

function base64UrlFromBase64(b64: string): string {
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function generateState(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return base64UrlEncode(array);
}

// ---------------------------------------------------------------------------
// Token types
// ---------------------------------------------------------------------------
interface TokenSet {
  accessToken: string;
  refreshToken: string | null;
  idToken: string | null;
  expiresAt: number; // epoch ms
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getValidAccessToken: () => Promise<string | null>;
}

// ---------------------------------------------------------------------------
// Secure token storage
// ---------------------------------------------------------------------------
async function persistTokens(tokens: TokenSet): Promise<void> {
  await AsyncStorage.multiSet([
    [STORAGE_KEYS.accessToken, tokens.accessToken],
    [STORAGE_KEYS.refreshToken, tokens.refreshToken ?? ''],
    [STORAGE_KEYS.expiresAt, String(tokens.expiresAt)],
    [STORAGE_KEYS.idToken, tokens.idToken ?? ''],
  ]);
}

async function loadTokens(): Promise<TokenSet | null> {
  const values = await AsyncStorage.multiGet([
    STORAGE_KEYS.accessToken,
    STORAGE_KEYS.refreshToken,
    STORAGE_KEYS.expiresAt,
    STORAGE_KEYS.idToken,
  ]);
  const map = Object.fromEntries(values);
  const accessToken = map[STORAGE_KEYS.accessToken];
  if (!accessToken) return null;
  return {
    accessToken,
    refreshToken: map[STORAGE_KEYS.refreshToken] || null,
    idToken: map[STORAGE_KEYS.idToken] || null,
    expiresAt: Number(map[STORAGE_KEYS.expiresAt]) || 0,
  };
}

async function clearTokens(): Promise<void> {
  await AsyncStorage.multiRemove(Object.values(STORAGE_KEYS));
}

// ---------------------------------------------------------------------------
// Token exchange & refresh (no client_secret – PKCE protects the exchange)
// ---------------------------------------------------------------------------
async function exchangeCodeForTokens(code: string, codeVerifier: string): Promise<TokenSet> {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: OAUTH_CONFIG.redirectUri,
    client_id: OAUTH_CONFIG.clientId,
    code_verifier: codeVerifier, // PKCE proof – replaces client_secret
  });

  const response = await fetch(OAUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Token exchange failed (${response.status}): ${errorBody}`);
  }

  const data = await response.json();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token ?? null,
    idToken: data.id_token ?? null,
    expiresAt: Date.now() + data.expires_in * 1000,
  };
}

async function refreshAccessToken(refreshToken: string): Promise<TokenSet> {
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: OAUTH_CONFIG.clientId,
    // No client_secret – public client refresh per RFC 6749 §2.1
  });

  const response = await fetch(OAUTH_CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Token refresh failed (${response.status}): ${errorBody}`);
  }

  const data = await response.json();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token ?? refreshToken, // rotation support
    idToken: data.id_token ?? null,
    expiresAt: Date.now() + data.expires_in * 1000,
  };
}

async function revokeToken(token: string): Promise<void> {
  try {
    await fetch(OAUTH_CONFIG.revocationEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        token,
        client_id: OAUTH_CONFIG.clientId,
      }).toString(),
    });
  } catch {
    // Best-effort revocation; local tokens are cleared regardless
  }
}

// ---------------------------------------------------------------------------
// Auth context & provider
// ---------------------------------------------------------------------------
const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  accessToken: null,
  login: async () => {},
  logout: async () => {},
  getValidAccessToken: async () => null,
});

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [tokens, setTokens] = useState<TokenSet | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Schedule automatic refresh before token expires
  const scheduleRefresh = useCallback((tokenSet: TokenSet) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    if (!tokenSet.refreshToken) return;

    const delay = Math.max(0, tokenSet.expiresAt - Date.now() - REFRESH_BUFFER_MS);
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const refreshed = await refreshAccessToken(tokenSet.refreshToken!);
        await persistTokens(refreshed);
        setTokens(refreshed);
        scheduleRefresh(refreshed);
      } catch {
        // Refresh failed – clear session, user will need to re-authenticate
        await clearTokens();
        setTokens(null);
      }
    }, delay);
  }, []);

  // Restore session on mount
  useEffect(() => {
    (async () => {
      try {
        const stored = await loadTokens();
        if (stored) {
          if (stored.expiresAt > Date.now()) {
            setTokens(stored);
            scheduleRefresh(stored);
          } else if (stored.refreshToken) {
            const refreshed = await refreshAccessToken(stored.refreshToken);
            await persistTokens(refreshed);
            setTokens(refreshed);
            scheduleRefresh(refreshed);
          } else {
            await clearTokens();
          }
        }
      } catch {
        await clearTokens();
      } finally {
        setIsLoading(false);
      }
    })();
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [scheduleRefresh]);

  const login = useCallback(async () => {
    const codeVerifier = await generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    const state = generateState();

    const authUrl =
      `${OAUTH_CONFIG.authorizationEndpoint}?` +
      new URLSearchParams({
        response_type: 'code',
        client_id: OAUTH_CONFIG.clientId,
        redirect_uri: OAUTH_CONFIG.redirectUri,
        scope: OAUTH_CONFIG.scopes.join(' '),
        state,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      }).toString();

    const result = await WebBrowser.openAuthSessionAsync(authUrl, OAUTH_CONFIG.redirectUri);

    if (result.type !== 'success' || !result.url) return;

    const params = new URL(result.url).searchParams;

    if (params.get('state') !== state) {
      throw new Error('OAuth state mismatch – possible CSRF attack');
    }

    const error = params.get('error');
    if (error) {
      throw new Error(`Authorization error: ${error} – ${params.get('error_description')}`);
    }

    const code = params.get('code');
    if (!code) throw new Error('No authorization code received');

    const tokenSet = await exchangeCodeForTokens(code, codeVerifier);
    await persistTokens(tokenSet);
    setTokens(tokenSet);
    scheduleRefresh(tokenSet);
  }, [scheduleRefresh]);

  const logout = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    if (tokens?.refreshToken) await revokeToken(tokens.refreshToken);
    await clearTokens();
    setTokens(null);
  }, [tokens]);

  const getValidAccessToken = useCallback(async (): Promise<string | null> => {
    if (!tokens) return null;
    if (tokens.expiresAt > Date.now() + REFRESH_BUFFER_MS) {
      return tokens.accessToken;
    }
    if (!tokens.refreshToken) return null;
    const refreshed = await refreshAccessToken(tokens.refreshToken);
    await persistTokens(refreshed);
    setTokens(refreshed);
    scheduleRefresh(refreshed);
    return refreshed.accessToken;
  }, [tokens, scheduleRefresh]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: tokens !== null,
        isLoading,
        accessToken: tokens?.accessToken ?? null,
        login,
        logout,
        getValidAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Screens
// ---------------------------------------------------------------------------
function LoginScreen() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    try {
      setError(null);
      await login();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <View style={styles.centered}>
      <Text style={styles.title}>Welcome</Text>
      <Text style={styles.subtitle}>Sign in to continue</Text>
      <Button title="Sign In" onPress={handleLogin} />
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

function HomeScreen() {
  const { logout, getValidAccessToken } = useAuth();
  const [profile, setProfile] = useState<string>('');

  useEffect(() => {
    (async () => {
      const token = await getValidAccessToken();
      if (token) {
        setProfile(`Authenticated\nToken: ${token.slice(0, 12)}…`);
      }
    })();
  }, [getValidAccessToken]);

  return (
    <View style={styles.centered}>
      <Text style={styles.title}>Home</Text>
      <Text style={styles.body}>{profile}</Text>
      <Button title="Sign Out" onPress={logout} />
    </View>
  );
}

// ---------------------------------------------------------------------------
// App root
// ---------------------------------------------------------------------------
export default function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return isAuthenticated ? <HomeScreen /> : <LoginScreen />;
}

export function AppRoot() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 16, color: '#666', marginBottom: 24 },
  body: { fontSize: 14, textAlign: 'center', marginBottom: 24, color: '#333' },
  error: { marginTop: 16, color: 'red', textAlign: 'center' },
});
