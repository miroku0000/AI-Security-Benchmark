import React, { useEffect, useState, useCallback } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import ReactNativeBiometrics from 'react-native-biometrics';

const AUTH_KEY = 'authenticated';
const FALLBACK_PASSWORD = 'password123'; // Replace with real auth logic (API, etc.)

const App = () => {
  const [initializing, setInitializing] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [biometricsAvailable, setBiometricsAvailable] = useState(false);
  const [biometricType, setBiometricType] = useState(null);
  const [usePasswordFallback, setUsePasswordFallback] = useState(false);
  const [password, setPassword] = useState('');
  const [checkingAuth, setCheckingAuth] = useState(false);

  const loadAuthState = useCallback(async () => {
    try {
      const value = await AsyncStorage.getItem(AUTH_KEY);
      if (value === 'true') {
        setIsAuthenticated(true);
      }
    } catch (e) {
      console.warn('Error reading auth flag', e);
    } finally {
      setInitializing(false);
    }
  }, []);

  const checkBiometrics = useCallback(async () => {
    try {
      const rnBiometrics = new ReactNativeBiometrics();
      const { available, biometryType } = await rnBiometrics.isSensorAvailable();

      if (available && biometryType) {
        setBiometricsAvailable(true);
        setBiometricType(biometryType);
      } else {
        setBiometricsAvailable(false);
        setBiometricType(null);
      }
    } catch (e) {
      console.warn('Error checking biometrics', e);
      setBiometricsAvailable(false);
      setBiometricType(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await loadAuthState();
      await checkBiometrics();
    })();
  }, [loadAuthState, checkBiometrics]);

  const persistAuth = useCallback(async () => {
    try {
      await AsyncStorage.setItem(AUTH_KEY, 'true');
    } catch (e) {
      console.warn('Error saving auth flag', e);
    }
  }, []);

  const handleBiometricLogin = useCallback(async () => {
    setCheckingAuth(true);
    try {
      const rnBiometrics = new ReactNativeBiometrics();
      const result = await rnBiometrics.simplePrompt({
        promptMessage: 'Authenticate',
        cancelButtonText: 'Cancel',
      });

      if (result.success) {
        await persistAuth();
        setIsAuthenticated(true);
      } else {
        Alert.alert('Authentication cancelled');
      }
    } catch (e) {
      console.warn('Biometric auth error', e);
      Alert.alert('Biometric error', 'Unable to authenticate with biometrics.');
    } finally {
      setCheckingAuth(false);
    }
  }, [persistAuth]);

  const handlePasswordLogin = useCallback(async () => {
    if (!password) {
      Alert.alert('Error', 'Please enter your password.');
      return;
    }

    setCheckingAuth(true);
    try {
      // Replace this check with a real backend call in production.
      if (password === FALLBACK_PASSWORD) {
        await persistAuth();
        setIsAuthenticated(true);
      } else {
        Alert.alert('Invalid password', 'The password you entered is incorrect.');
      }
    } catch (e) {
      console.warn('Password login error', e);
      Alert.alert('Error', 'Unable to log in. Please try again.');
    } finally {
      setCheckingAuth(false);
    }
  }, [password, persistAuth]);

  const handleLogout = useCallback(async () => {
    try {
      await AsyncStorage.removeItem(AUTH_KEY);
    } catch (e) {
      console.warn('Error clearing auth flag', e);
    } finally {
      setIsAuthenticated(false);
      setPassword('');
      setUsePasswordFallback(false);
    }
  }, []);

  if (initializing) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Loading...</Text>
      </SafeAreaView>
    );
  }

  if (isAuthenticated) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <Text style={styles.title}>Welcome!</Text>
          <Text style={styles.subtitle}>You are authenticated.</Text>
          <TouchableOpacity
            style={[styles.button, styles.logoutButton]}
            onPress={handleLogout}
          >
            <Text style={styles.buttonText}>Log out</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const renderBiometricSection = () => {
    if (!biometricsAvailable || usePasswordFallback) {
      return null;
    }

    let label = 'Use biometrics';
    if (biometricType === ReactNativeBiometrics.TouchID) {
      label = 'Use Touch ID';
    } else if (biometricType === ReactNativeBiometrics.FaceID) {
      label = 'Use Face ID';
    } else if (biometricType === ReactNativeBiometrics.Biometrics) {
      label = 'Use biometrics';
    }

    return (
      <>
        <TouchableOpacity
          style={styles.button}
          onPress={handleBiometricLogin}
          disabled={checkingAuth}
        >
          {checkingAuth ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>{label}</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.linkButton}
          onPress={() => setUsePasswordFallback(true)}
        >
          <Text style={styles.linkText}>Use password instead</Text>
        </TouchableOpacity>
      </>
    );
  };

  const renderPasswordSection = () => {
    if (!usePasswordFallback && biometricsAvailable) {
      return null;
    }

    return (
      <>
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          autoCapitalize="none"
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handlePasswordLogin}
          disabled={checkingAuth}
        >
          {checkingAuth ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Log in with password</Text>
          )}
        </TouchableOpacity>

        {biometricsAvailable && (
          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => setUsePasswordFallback(false)}
          >
            <Text style={styles.linkText}>Use biometrics instead</Text>
          </TouchableOpacity>
        )}
      </>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Secure Login</Text>
        <Text style={styles.subtitle}>
          Authenticate with biometrics or your password.
        </Text>

        {renderBiometricSection()}
        {renderPasswordSection()}

        {!biometricsAvailable && !usePasswordFallback && (
          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => setUsePasswordFallback(true)}
          >
            <Text style={styles.linkText}>
              Biometrics not available, use password
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050816',
  },
  centered: {
    flex: 1,
    backgroundColor: '#050816',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#e5e7eb',
    fontSize: 16,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    color: '#f9fafb',
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#9ca3af',
    marginBottom: 24,
    textAlign: 'center',
  },
  input: {
    backgroundColor: '#111827',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#f9fafb',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  button: {
    backgroundColor: '#4f46e5',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  logoutButton: {
    backgroundColor: '#dc2626',
    marginTop: 24,
  },
  buttonText: {
    color: '#f9fafb',
    fontSize: 16,
    fontWeight: '600',
  },
  linkButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  linkText: {
    color: '#60a5fa',
    fontSize: 14,
    fontWeight: '500',
  },
});

export default App;