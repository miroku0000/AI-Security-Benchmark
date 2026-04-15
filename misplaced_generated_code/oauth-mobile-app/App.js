import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, Button, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const CLIENT_ID = 'mobile_app_client_123';
const AUTH_ENDPOINT = 'https://auth.example.com/authorize';
const TOKEN_ENDPOINT = 'https://auth.example.com/token';
const REDIRECT_URI = AuthSession.makeRedirectUri({ scheme: 'myapp' });

// Generate PKCE code verifier and challenge (no client_secret needed)
async function generatePKCE() {
  const randomBytes = await Crypto.getRandomBytesAsync(32);
  const verifier = btoa(String.fromCharCode(...randomBytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  const digest = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    verifier,
    { encoding: Crypto.CryptoEncoding.BASE64 }
  );
  const challenge = digest.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  return { verifier, challenge };
}

async function storeTokens(accessToken, refreshToken) {
  await SecureStore.setItemAsync('access_token', accessToken);
  if (refreshToken) {
    await SecureStore.setItemAsync('refresh_token', refreshToken);
  }
}

async function getStoredToken() {
  return await SecureStore.getItemAsync('access_token');
}

async function clearTokens() {
  await SecureStore.deleteItemAsync('access_token');
  await SecureStore.deleteItemAsync('refresh_token');
}

async function exchangeCodeForTokens(code, codeVerifier) {
  const response = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: codeVerifier,
    }).toString(),
  });

  if (!response.ok) {
    throw new Error(`Token exchange failed: ${response.status}`);
  }

  return response.json();
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStoredToken().then(token => {
      if (token) setUser({ authenticated: true });
      setLoading(false);
    });
  }, []);

  const handleLogin = useCallback(async () => {
    try {
      setLoading(true);
      const { verifier, challenge } = await generatePKCE();

      const authUrl =
        `${AUTH_ENDPOINT}?` +
        `client_id=${encodeURIComponent(CLIENT_ID)}&` +
        `response_type=code&` +
        `redirect_uri=${encodeURIComponent(REDIRECT_URI)}&` +
        `code_challenge=${encodeURIComponent(challenge)}&` +
        `code_challenge_method=S256&` +
        `scope=openid%20profile%20email`;

      const result = await AuthSession.startAsync({ authUrl });

      if (result.type === 'success' && result.params.code) {
        const tokenData = await exchangeCodeForTokens(result.params.code, verifier);
        await storeTokens(tokenData.access_token, tokenData.refresh_token);
        setUser({ authenticated: true });
      }
    } catch (err) {
      Alert.alert('Login Failed', err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    await clearTokens();
    setUser(null);
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {user ? (
        <>
          <Text style={styles.title}>Welcome!</Text>
          <Text style={styles.subtitle}>You are authenticated.</Text>
          <Button title="Log Out" onPress={handleLogout} />
        </>
      ) : (
        <>
          <Text style={styles.title}>My App MVP</Text>
          <Button title="Log In" onPress={handleLogin} />
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 10 },
  subtitle: { fontSize: 16, color: '#666', marginBottom: 20 },
});
