import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import ReactNativeBiometrics, { BiometryTypes } from 'react-native-biometrics';

const AUTHENTICATED_FLAG_KEY = 'auth:isAuthenticated';
const DEMO_PASSWORD = 'password123';
const rnBiometrics = new ReactNativeBiometrics();

const App = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isBiometricAvailable, setIsBiometricAvailable] = useState(false);
  const [biometryType, setBiometryType] = useState(null);
  const [password, setPassword] = useState('');

  const biometricLabel = useMemo(() => {
    if (biometryType === BiometryTypes.FaceID) {
      return 'Face ID';
    }

    if (biometryType === BiometryTypes.TouchID) {
      return 'Touch ID';
    }

    if (biometryType === BiometryTypes.Biometrics && Platform.OS === 'android') {
      return 'Fingerprint';
    }

    return 'Biometrics';
  }, [biometryType]);

  useEffect(() => {
    const bootstrapAuth = async () => {
      try {
        const storedFlag = await AsyncStorage.getItem(AUTHENTICATED_FLAG_KEY);
        const { available, biometryType: availableBiometryType } = await rnBiometrics.isSensorAvailable();

        setIsBiometricAvailable(Boolean(available));
        setBiometryType(availableBiometryType ?? null);

        if (storedFlag === 'true') {
          setIsAuthenticated(true);
        }
      } catch (error) {
        setIsBiometricAvailable(false);
        setBiometryType(null);
      } finally {
        setIsLoading(false);
      }
    };

    bootstrapAuth();
  }, []);

  const completeAuthentication = async () => {
    await AsyncStorage.setItem(AUTHENTICATED_FLAG_KEY, 'true');
    setPassword('');
    setIsAuthenticated(true);
  };

  const handleBiometricLogin = async () => {
    try {
      const { success } = await rnBiometrics.simplePrompt({
        promptMessage: `Verify with ${biometricLabel}`,
        cancelButtonText: 'Use Password',
      });

      if (!success) {
        Alert.alert('Authentication failed', 'Biometric verification was not successful.');
        return;
      }

      await completeAuthentication();
    } catch (error) {
      Alert.alert('Authentication cancelled', 'Use your password to continue.');
    }
  };

  const handlePasswordLogin = async () => {
    if (!password.trim()) {
      Alert.alert('Password required', 'Enter your password to continue.');
      return;
    }

    if (password !== DEMO_PASSWORD) {
      Alert.alert('Login failed', 'The password you entered is incorrect.');
      return;
    }

    await completeAuthentication();
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem(AUTHENTICATED_FLAG_KEY);
    setPassword('');
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Checking authentication state...</Text>
      </SafeAreaView>
    );
  }

  if (isAuthenticated) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.card}>
          <Text style={styles.title}>Home</Text>
          <Text style={styles.subtitle}>You are signed in.</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={handleLogout}>
            <Text style={styles.primaryButtonText}>Log Out</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Login</Text>
        <Text style={styles.subtitle}>
          {isBiometricAvailable
            ? `Sign in with ${biometricLabel} or use your password.`
            : 'Biometric authentication is not available on this device. Use your password.'}
        </Text>

        {isBiometricAvailable ? (
          <TouchableOpacity style={styles.primaryButton} onPress={handleBiometricLogin}>
            <Text style={styles.primaryButtonText}>Continue with {biometricLabel}</Text>
          </TouchableOpacity>
        ) : null}

        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setPassword}
          placeholder="Password"
          placeholderTextColor="#94a3b8"
          secureTextEntry
          style={styles.input}
          value={password}
        />

        <Text style={styles.hint}>Demo password: {DEMO_PASSWORD}</Text>

        <TouchableOpacity style={styles.secondaryButton} onPress={handlePasswordLogin}>
          <Text style={styles.secondaryButtonText}>Continue with Password</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8fafc',
    padding: 24,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8fafc',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 3,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0f172a',
    textAlign: 'center',
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    lineHeight: 22,
    color: '#475569',
    textAlign: 'center',
    marginBottom: 24,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#475569',
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#0f172a',
    marginBottom: 12,
  },
  hint: {
    textAlign: 'center',
    color: '#64748b',
    marginBottom: 16,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 16,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#0f172a',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default App;