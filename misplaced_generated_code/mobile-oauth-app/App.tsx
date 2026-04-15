import { StatusBar } from 'expo-status-bar';
import React from 'react';
import {
  ActivityIndicator,
  Button,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AuthProvider, useAuth } from './src/auth/AuthContext';

function Screen() {
  const { tokens, isLoading, error, signIn, signOut, getAccessToken } =
    useAuth();
  const [resolved, setResolved] = React.useState<string | null>(null);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>OAuth 2.0</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {tokens ? (
        <>
          <Text style={styles.label}>Signed in</Text>
          <Text style={styles.mono} numberOfLines={3}>
            {tokens.accessToken}
          </Text>
          <Button title="Get valid access token" onPress={async () => {
            const t = await getAccessToken();
            setResolved(t);
          }} />
          {resolved ? (
            <Text style={styles.monoSmall} numberOfLines={4}>
              {resolved}
            </Text>
          ) : null}
          <Button title="Sign out" onPress={signOut} />
        </>
      ) : (
        <Button title="Sign in" onPress={signIn} />
      )}
      <StatusBar style="auto" />
    </ScrollView>
  );
}

export default function App() {
  return (
    <SafeAreaView style={styles.safe}>
      <AuthProvider>
        <Screen />
      </AuthProvider>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  container: { padding: 24, gap: 12 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
  label: { fontSize: 16, fontWeight: '500' },
  mono: { fontFamily: 'Courier', fontSize: 12 },
  monoSmall: { fontFamily: 'Courier', fontSize: 11 },
  error: { color: '#b00020', marginBottom: 8 },
});
