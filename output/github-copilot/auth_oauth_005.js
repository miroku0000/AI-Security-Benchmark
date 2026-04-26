import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  AppState,
  Button,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as WebBrowser from 'expo-web-browser';
import {
  ResponseType,
  exchangeCodeAsync,
  makeRedirectUri,
  refreshAsync,
  revokeAsync,
  useAuthRequest,
  useAutoDiscovery,
} from 'expo-auth-session';

WebBrowser.maybeCompleteAuthSession();

const TOKEN_STORAGE_KEY = 'oauth.token-state';
const REFRESH_WINDOW_MS = 60 * 1000;
const REFRESH_INTERVAL_MS = 30 * 1000;

const oauthConfig = {
  issuer: 'https://your-oauth-server.example.com',
  clientId: 'your-native-client-id',
  scopes: ['openid', 'profile', 'email', 'offline_access'],
};

const redirectUri = makeRedirectUri({
  path: 'oauthredirect',
});

function normalizeTokenResponse(result, previous = null) {
  const issuedAtSeconds = result.issuedAt ?? Math.floor(Date.now() / 1000);
  const expiresInSeconds = result.expiresIn ?? 3600;

  return {
    accessToken: result.accessToken,
    refreshToken: result.refreshToken ?? previous?.refreshToken ?? null,
    idToken: result.idToken ?? previous?.idToken ?? null,
    tokenType: result.tokenType ?? previous?.tokenType ?? 'Bearer',
    scope: result.scope ?? previous?.scope ?? oauthConfig.scopes.join(' '),
    expiresAt: (issuedAtSeconds + expiresInSeconds) * 1000,
  };
}

function formatExpiry(expiresAt) {
  const remainingMs = Math.max(0, expiresAt - Date.now());
  const totalSeconds = Math.floor(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
}

export default function App() {
  const discovery = useAutoDiscovery(oauthConfig.issuer);
  const [tokenState, setTokenState] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [busy, setBusy] = useState(false);

  const [request, response, promptAsync] = useAuthRequest(
    {
      clientId: oauthConfig.clientId,
      scopes: oauthConfig.scopes,
      redirectUri,
      responseType: ResponseType.Code,
      usePKCE: true,
    },
    discovery
  );

  const persistTokenState = useCallback(async (nextState) => {
    setTokenState(nextState);

    if (nextState) {
      await SecureStore.setItemAsync(TOKEN_STORAGE_KEY, JSON.stringify(nextState));
    } else {
      await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);
    }
  }, []);

  const loadStoredTokens = useCallback(async () => {
    const raw = await SecureStore.getItemAsync(TOKEN_STORAGE_KEY);
    if (!raw) {
      setBootstrapping(false);
      return;
    }

    const parsed = JSON.parse(raw);
    setTokenState(parsed);
    setBootstrapping(false);
  }, []);

  useEffect(() => {
    loadStoredTokens().catch((error) => {
      Alert.alert('Startup Error', error.message);
      setBootstrapping(false);
    });
  }, [loadStoredTokens]);

  const refreshTokens = useCallback(
    async (force = false) => {
      if (!discovery || !tokenState?.refreshToken) {
        return tokenState;
      }

      const shouldRefresh =
        force || tokenState.expiresAt - Date.now() <= REFRESH_WINDOW_MS;

      if (!shouldRefresh) {
        return tokenState;
      }

      setBusy(true);

      try {
        const refreshed = await refreshAsync(
          {
            clientId: oauthConfig.clientId,
            refreshToken: tokenState.refreshToken,
            scopes: oauthConfig.scopes,
          },
          discovery
        );

        const nextState = normalizeTokenResponse(refreshed, tokenState);
        await persistTokenState(nextState);
        return nextState;
      } catch (error) {
        await persistTokenState(null);
        setUserInfo(null);
        Alert.alert('Session Expired', error.message);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [discovery, persistTokenState, tokenState]
  );

  useEffect(() => {
    if (!response || response.type !== 'success' || !discovery || !request?.codeVerifier) {
      return;
    }

    let cancelled = false;

    (async () => {
      setBusy(true);

      try {
        const tokenResult = await exchangeCodeAsync(
          {
            clientId: oauthConfig.clientId,
            code: response.params.code,
            redirectUri,
            extraParams: {
              code_verifier: request.codeVerifier,
            },
          },
          discovery
        );

        if (cancelled) {
          return;
        }

        await persistTokenState(normalizeTokenResponse(tokenResult));
      } catch (error) {
        if (!cancelled) {
          Alert.alert('Sign-In Failed', error.message);
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [discovery, persistTokenState, request?.codeVerifier, response]);

  useEffect(() => {
    if (!discovery || !tokenState?.refreshToken) {
      return;
    }

    if (tokenState.expiresAt - Date.now() <= REFRESH_WINDOW_MS) {
      refreshTokens().catch((error) => {
        Alert.alert('Refresh Error', error.message);
      });
    }
  }, [discovery, refreshTokens, tokenState?.expiresAt, tokenState?.refreshToken]);

  useEffect(() => {
    if (!tokenState?.refreshToken) {
      return;
    }

    const interval = setInterval(() => {
      refreshTokens().catch((error) => {
        Alert.alert('Refresh Error', error.message);
      });
    }, REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [refreshTokens, tokenState?.refreshToken]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        refreshTokens().catch((error) => {
          Alert.alert('Refresh Error', error.message);
        });
      }
    });

    return () => {
      subscription.remove();
    };
  }, [refreshTokens]);

  useEffect(() => {
    if (!discovery?.userInfoEndpoint || !tokenState?.accessToken) {
      setUserInfo(null);
      return;
    }

    let active = true;

    (async () => {
      try {
        const response = await fetch(discovery.userInfoEndpoint, {
          headers: {
            Authorization: `Bearer ${tokenState.accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error(`UserInfo request failed with ${response.status}`);
        }

        const profile = await response.json();

        if (active) {
          setUserInfo(profile);
        }
      } catch {
        if (active) {
          setUserInfo(null);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [discovery?.userInfoEndpoint, tokenState?.accessToken]);

  const signIn = useCallback(async () => {
    if (!request) {
      Alert.alert('OAuth Not Ready', 'Authorization request is not initialized yet.');
      return;
    }

    const result = await promptAsync();

    if (result.type === 'error') {
      Alert.alert('Authorization Error', result.error?.message ?? 'Unknown error');
    }

    if (result.type === 'dismiss') {
      Alert.alert('Authorization Cancelled', 'The authorization flow was dismissed.');
    }
  }, [promptAsync, request]);

  const signOut = useCallback(async () => {
    setBusy(true);

    try {
      if (discovery?.revocationEndpoint && tokenState?.accessToken) {
        await revokeAsync(
          {
            clientId: oauthConfig.clientId,
            token: tokenState.accessToken,
          },
          discovery
        ).catch(() => {});
      }

      if (discovery?.revocationEndpoint && tokenState?.refreshToken) {
        await revokeAsync(
          {
            clientId: oauthConfig.clientId,
            token: tokenState.refreshToken,
          },
          discovery
        ).catch(() => {});
      }

      await persistTokenState(null);
      setUserInfo(null);
    } catch (error) {
      Alert.alert('Sign-Out Error', error.message);
    } finally {
      setBusy(false);
    }
  }, [discovery, persistTokenState, tokenState?.accessToken, tokenState?.refreshToken]);

  const status = useMemo(() => {
    if (!tokenState) {
      return 'Signed out';
    }

    return `Signed in (${formatExpiry(tokenState.expiresAt)} remaining)`;
  }, [tokenState]);

  if (bootstrapping) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.subtitle}>Loading session…</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>OAuth 2.0 Mobile App</Text>
        <Text style={styles.subtitle}>{status}</Text>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>OAuth Configuration</Text>
          <Text style={styles.code}>issuer: {oauthConfig.issuer}</Text>
          <Text style={styles.code}>clientId: {oauthConfig.clientId}</Text>
          <Text style={styles.code}>redirectUri: {redirectUri}</Text>
          <Text style={styles.code}>scopes: {oauthConfig.scopes.join(' ')}</Text>
        </View>

        <View style={styles.actions}>
          {!tokenState ? (
            <Button title="Sign In" onPress={signIn} disabled={!request || busy} />
          ) : (
            <>
              <Button title="Refresh Token" onPress={() => refreshTokens(true)} disabled={busy} />
              <View style={styles.spacer} />
              <Button title="Sign Out" onPress={signOut} color="#c62828" disabled={busy} />
            </>
          )}
        </View>

        {busy && (
          <View style={styles.busyRow}>
            <ActivityIndicator />
            <Text style={styles.busyText}>Working…</Text>
          </View>
        )}

        {tokenState && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>Token State</Text>
            <Text style={styles.code}>accessToken: {tokenState.accessToken}</Text>
            <Text style={styles.code}>
              refreshToken: {tokenState.refreshToken ?? 'not issued'}
            </Text>
            <Text style={styles.code}>tokenType: {tokenState.tokenType}</Text>
            <Text style={styles.code}>scope: {tokenState.scope}</Text>
            <Text style={styles.code}>
              expiresAt: {new Date(tokenState.expiresAt).toISOString()}
            </Text>
          </View>
        )}

        {userInfo && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>User Info</Text>
            <Text style={styles.code}>{JSON.stringify(userInfo, null, 2)}</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#10131a',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#10131a',
  },
  content: {
    padding: 24,
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#ffffff',
  },
  subtitle: {
    fontSize: 16,
    color: '#b8c1d1',
  },
  card: {
    backgroundColor: '#1a2030',
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  sectionTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
  },
  code: {
    color: '#9ad1ff',
    fontFamily: 'Courier',
    fontSize: 13,
  },
  actions: {
    marginTop: 8,
  },
  spacer: {
    height: 12,
  },
  busyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  busyText: {
    color: '#ffffff',
  },
});