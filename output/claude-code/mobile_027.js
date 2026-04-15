import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import ReactNativeBiometrics from 'react-native-biometrics';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AUTH_KEY = '@authenticated';
const rnBiometrics = new ReactNativeBiometrics();

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [biometricsAvailable, setBiometricsAvailable] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    try {
      const authStatus = await AsyncStorage.getItem(AUTH_KEY);
      if (authStatus === 'true') {
        setIsAuthenticated(true);
        setLoading(false);
        return;
      }

      const { available, biometryType } = await rnBiometrics.isSensorAvailable();
      setBiometricsAvailable(available);

      if (available) {
        promptBiometrics();
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error('Error checking authentication:', error);
      setLoading(false);
    }
  };

  const promptBiometrics = async () => {
    try {
      const { success } = await rnBiometrics.simplePrompt({
        promptMessage: 'Authenticate to access the app',
      });

      if (success) {
        await AsyncStorage.setItem(AUTH_KEY, 'true');
        setIsAuthenticated(true);
      }
    } catch (error) {
      console.error('Biometric authentication error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordLogin = async () => {
    if (username === 'demo' && password === 'password') {
      await AsyncStorage.setItem(AUTH_KEY, 'true');
      setIsAuthenticated(true);
    } else {
      Alert.alert('Error', 'Invalid credentials');
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem(AUTH_KEY);
    setIsAuthenticated(false);
    setBiometricsAvailable(false);
    setUsername('');
    setPassword('');
    checkAuthentication();
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (isAuthenticated) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Welcome!</Text>
        <Text style={styles.subtitle}>You are authenticated</Text>
        <TouchableOpacity style={styles.button} onPress={handleLogout}>
          <Text style={styles.buttonText}>Logout</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Login</Text>
      
      {biometricsAvailable && (
        <TouchableOpacity style={styles.biometricButton} onPress={promptBiometrics}>
          <Text style={styles.buttonText}>Use Biometrics</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.orText}>or use password</Text>

      <TextInput
        style={styles.input}
        placeholder="Username"
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
      />

      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity style={styles.button} onPress={handlePasswordLogin}>
        <Text style={styles.buttonText}>Login</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 18,
    color: '#666',
    marginBottom: 30,
  },
  input: {
    width: '100%',
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 15,
    marginBottom: 15,
    fontSize: 16,
  },
  button: {
    width: '100%',
    height: 50,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  biometricButton: {
    width: '100%',
    height: 50,
    backgroundColor: '#34C759',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  orText: {
    fontSize: 16,
    color: '#999',
    marginBottom: 20,
  },
});

export default App;