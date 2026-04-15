import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';

WebBrowser.maybeCompleteAuthSession();

const CLIENT_ID = 'mobile_app_client_123';
const OAUTH_ISSUER = 'https://YOUR_IDP_ISSUER';
const TOKEN_PROXY_URL = 'http://127.0.0.1:8787/token';
const SCOPES = ['openid', 'profile', 'email'];

function OAuthScreen({ discovery }) {
  const [tokens, setTokens] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const exchangedRef = useRef(false);

  const redirectUri = useMemo(
    () =>
      AuthSession.makeRedirectUri({
        scheme: 'mobileoauthmvp',
        path: 'redirect',
      }),
    []
  );

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: CLIENT_ID,
      scopes: SCOPES,
      redirectUri,
      responseType: AuthSession.ResponseType.Code,
      usePKCE: true,
    },
    discovery
  );

  const exchangeViaProxy = useCallback(
    async (code) => {
      if (!request?.codeVerifier) {
        setError('Missing PKCE code_verifier');
        return;
      }
      setBusy(true);
      setError(null);
      try {
        const res = await fetch(TOKEN_PROXY_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            redirect_uri: redirectUri,
            code_verifier: request.codeVerifier,
          }),
        });
        const text = await res.text();
        let json;
        try {
          json = JSON.parse(text);
        } catch {
          json = { raw: text };
        }
        if (!res.ok) {
          setError(typeof json === 'object' ? JSON.stringify(json) : text);
          return;
        }
        setTokens(json);
      } catch (e) {
        setError(String(e?.message ?? e));
      } finally {
        setBusy(false);
      }
    },
    [request, redirectUri]
  );

  useEffect(() => {
    if (response?.type !== 'success' || exchangedRef.current) return;
    const { code } = response.params;
    if (!code) {
      setError('No authorization code');
      return;
    }
    exchangedRef.current = true;
    exchangeViaProxy(code);
  }, [response, exchangeViaProxy]);

  useEffect(() => {
    if (response?.type === 'error') {
      setError(response.error?.message ?? 'Authorization failed');
    }
  }, [response]);

  const signIn = async () => {
    exchangedRef.current = false;
    setError(null);
    setTokens(null);
    await promptAsync({ showInRecents: true });
  };

  const signOut = () => {
    setTokens(null);
    setError(null);
    exchangedRef.current = false;
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>OAuth 2.0 (PKCE + proxy)</Text>
      <Text style={styles.mono}>client_id: {CLIENT_ID}</Text>
      <Text style={styles.hint}>
        client_secret belongs on the token proxy server, not in the app binary.
      </Text>
      <Button title="Sign in with OAuth" onPress={signIn} disabled={!request || busy} />
      {busy ? <ActivityIndicator style={styles.spinner} /> : null}
      {error ? <Text style={styles.err}>{error}</Text> : null}
      {tokens ? (
        <View style={styles.box}>
          <Text style={styles.subtitle}>Token response</Text>
          <Text selectable style={styles.monoSmall}>
            {JSON.stringify(tokens, null, 2)}
          </Text>
          <Button title="Clear session" onPress={signOut} />
        </View>
      ) : null}
    </ScrollView>
  );
}

export default function App() {
  const [discovery, setDiscovery] = useState(null);
  const [loadingDiscovery, setLoadingDiscovery] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await AuthSession.fetchDiscoveryAsync(OAUTH_ISSUER);
        if (!cancelled) setDiscovery(d);
      } catch (e) {
        if (!cancelled) setLoadError(String(e?.message ?? e));
      } finally {
        if (!cancelled) setLoadingDiscovery(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadingDiscovery) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.hint}>Loading OAuth discovery…</Text>
      </View>
    );
  }

  if (!discovery) {
    return (
      <View style={styles.centered}>
        <Text style={styles.err}>Set OAUTH_ISSUER in App.js to your IdP issuer URL.</Text>
        {loadError ? <Text style={styles.err}>{loadError}</Text> : null}
      </View>
    );
  }

  return <OAuthScreen discovery={discovery} />;
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    paddingTop: 56,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  hint: {
    marginVertical: 12,
    color: '#444',
  },
  mono: {
    fontFamily: 'Courier',
    fontSize: 13,
  },
  monoSmall: {
    fontFamily: 'Courier',
    fontSize: 11,
    marginBottom: 12,
  },
  err: {
    color: '#b00020',
    marginTop: 12,
  },
  box: {
    marginTop: 20,
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  spinner: {
    marginTop: 16,
  },
});
