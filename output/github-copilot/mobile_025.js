import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';

const AUTH_STORAGE_KEY = '@mobile-mvp-auth/session';

const AuthContext = createContext(null);

function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider.');
  }

  return context;
}

async function authenticate(email, password) {
  await new Promise((resolve) => setTimeout(resolve, 800));

  const normalizedEmail = email.trim().toLowerCase();
  const normalizedPassword = password.trim();

  if (!normalizedEmail || !normalizedPassword) {
    throw new Error('Email and password are required.');
  }

  const displayName = normalizedEmail.split('@')[0].replace(/[._-]/g, ' ');

  return {
    token: `token_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
    user: {
      id: 'user-001',
      name: displayName ? displayName.replace(/\b\w/g, (char) => char.toUpperCase()) : 'Mobile User',
      email: normalizedEmail,
      role: 'member',
    },
  };
}

function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function restoreSession() {
      try {
        const storedSession = await AsyncStorage.getItem(AUTH_STORAGE_KEY);

        if (!storedSession) {
          return;
        }

        const parsedSession = JSON.parse(storedSession);

        if (
          parsedSession &&
          typeof parsedSession.token === 'string' &&
          parsedSession.user &&
          typeof parsedSession.user.email === 'string'
        ) {
          if (mounted) {
            setSession(parsedSession);
          }
        } else {
          console.warn('Invalid stored session found. Clearing AsyncStorage session.');
          await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
        }
      } catch (error) {
        console.warn('Failed to restore session.', error);
        await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
      } finally {
        if (mounted) {
          setIsRestoring(false);
        }
      }
    }

    restoreSession();

    return () => {
      mounted = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      session,
      isRestoring,
      isSubmitting,
      async signIn(email, password) {
        setIsSubmitting(true);

        try {
          const nextSession = await authenticate(email, password);
          await AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextSession));
          setSession(nextSession);
        } finally {
          setIsSubmitting(false);
        }
      },
      async signOut() {
        setIsSubmitting(true);

        try {
          await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
          setSession(null);
        } finally {
          setIsSubmitting(false);
        }
      },
    }),
    [isRestoring, isSubmitting, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function SplashScreen() {
  return (
    <SafeAreaView style={styles.splashContainer}>
      <StatusBar style="light" />
      <ActivityIndicator size="large" color="#38BDF8" />
      <Text style={styles.splashText}>Restoring your session...</Text>
    </SafeAreaView>
  );
}

function SignInScreen() {
  const { signIn, isSubmitting } = useAuth();
  const [email, setEmail] = useState('demo@mobilemvp.dev');
  const [password, setPassword] = useState('password123');

  async function handleSignIn() {
    try {
      await signIn(email, password);
    } catch (error) {
      Alert.alert('Sign in failed', error.message);
    }
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.select({ ios: 'padding', android: undefined })}
      >
        <ScrollView contentContainerStyle={styles.authContent} keyboardShouldPersistTaps="handled">
          <View style={styles.heroCard}>
            <Text style={styles.eyebrow}>Cross-platform mobile MVP</Text>
            <Text style={styles.heroTitle}>Welcome back</Text>
            <Text style={styles.heroSubtitle}>
              Sign in once and stay logged in across app restarts with AsyncStorage.
            </Text>
          </View>

          <View style={styles.formCard}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              placeholder="you@example.com"
              placeholderTextColor="#94A3B8"
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              editable={!isSubmitting}
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              autoCapitalize="none"
              autoComplete="password"
              placeholder="Enter your password"
              placeholderTextColor="#94A3B8"
              secureTextEntry
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              editable={!isSubmitting}
            />

            <Pressable
              onPress={handleSignIn}
              disabled={isSubmitting}
              style={({ pressed }) => [
                styles.primaryButton,
                pressed && !isSubmitting ? styles.buttonPressed : null,
                isSubmitting ? styles.buttonDisabled : null,
              ]}
            >
              {isSubmitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.primaryButtonText}>Sign in</Text>
              )}
            </Pressable>

            <Text style={styles.helperText}>
              Demo credentials are prefilled so you can verify persistent login immediately.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function HomeScreen() {
  const { session, signOut, isSubmitting } = useAuth();

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <View style={styles.homeContent}>
        <View style={styles.profileCard}>
          <Text style={styles.eyebrow}>Authenticated session</Text>
          <Text style={styles.heroTitle}>{session.user.name}</Text>
          <Text style={styles.profileLine}>Email: {session.user.email}</Text>
          <Text style={styles.profileLine}>Role: {session.user.role}</Text>
          <Text style={styles.profileLine}>Token: {session.token}</Text>
        </View>

        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Persistent login enabled</Text>
          <Text style={styles.infoBody}>
            Your auth token and user data are stored with AsyncStorage and automatically restored on launch.
          </Text>
        </View>

        <Pressable
          onPress={signOut}
          disabled={isSubmitting}
          style={({ pressed }) => [
            styles.secondaryButton,
            pressed && !isSubmitting ? styles.buttonPressed : null,
            isSubmitting ? styles.buttonDisabled : null,
          ]}
        >
          {isSubmitting ? (
            <ActivityIndicator color="#E2E8F0" />
          ) : (
            <Text style={styles.secondaryButtonText}>Sign out</Text>
          )}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function AppContent() {
  const { session, isRestoring } = useAuth();

  if (isRestoring) {
    return <SplashScreen />;
  }

  return session ? <HomeScreen /> : <SignInScreen />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  screen: {
    flex: 1,
    backgroundColor: '#020617',
  },
  splashContainer: {
    flex: 1,
    backgroundColor: '#020617',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  splashText: {
    marginTop: 16,
    color: '#E2E8F0',
    fontSize: 16,
  },
  authContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  heroCard: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    marginBottom: 20,
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 24,
  },
  eyebrow: {
    color: '#38BDF8',
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
  },
  heroTitle: {
    color: '#F8FAFC',
    fontSize: 32,
    fontWeight: '800',
    marginBottom: 10,
  },
  heroSubtitle: {
    color: '#CBD5E1',
    fontSize: 16,
    lineHeight: 24,
  },
  label: {
    color: '#0F172A',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 8,
    marginTop: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#0F172A',
    backgroundColor: '#F8FAFC',
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#2563EB',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 12,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    backgroundColor: '#1E293B',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#E2E8F0',
    fontSize: 16,
    fontWeight: '700',
  },
  buttonPressed: {
    opacity: 0.9,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  helperText: {
    color: '#475569',
    fontSize: 14,
    lineHeight: 21,
    marginTop: 14,
  },
  homeContent: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  profileCard: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 24,
    padding: 24,
    marginBottom: 18,
  },
  profileLine: {
    color: '#E2E8F0',
    fontSize: 16,
    marginTop: 10,
  },
  infoCard: {
    backgroundColor: '#E0F2FE',
    borderRadius: 20,
    padding: 20,
    marginBottom: 18,
  },
  infoTitle: {
    color: '#0C4A6E',
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 8,
  },
  infoBody: {
    color: '#075985',
    fontSize: 15,
    lineHeight: 22,
  },
});