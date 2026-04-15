export const ENCRYPTION_KEY = 'REPLACE_WITH_A_SECURE_RANDOM_KEY_STRING';

// utils/encryptionUtils.js
import CryptoJS from 'crypto-js';
import { ENCRYPTION_KEY } from '../config/encryptionConfig';

export const encryptData = (plainText) => {
  if (!plainText) return '';
  const cipher = CryptoJS.AES.encrypt(plainText, ENCRYPTION_KEY);
  return cipher.toString();
};

export const decryptData = (cipherText) => {
  if (!cipherText) return '';
  try {
    const bytes = CryptoJS.AES.decrypt(cipherText, ENCRYPTION_KEY);
    const decrypted = bytes.toString(CryptoJS.enc.Utf8);
    return decrypted || '';
  } catch (e) {
    console.warn('Decryption failed:', e);
    return '';
  }
};

export const encryptJson = (value) => {
  const json = JSON.stringify(value ?? null);
  return encryptData(json);
};

export const decryptJson = (cipherText) => {
  const decrypted = decryptData(cipherText);
  if (!decrypted) return null;
  try {
    return JSON.parse(decrypted);
  } catch (e) {
    console.warn('JSON parse failed after decryption:', e);
    return null;
  }
};

// services/secureStorageService.js
import AsyncStorage from '@react-native-async-storage/async-storage';
import { encryptJson, decryptJson } from '../utils/encryptionUtils';

const KEYS = {
  USER_PROFILE: 'secure:user_profile',
  PAYMENT_INFO: 'secure:payment_info',
  AUTH_TOKEN: 'secure:auth_token',
};

export const setEncryptedItem = async (key, value) => {
  try {
    const encrypted = encryptJson(value);
    await AsyncStorage.setItem(key, encrypted);
  } catch (e) {
    console.warn('Error setting encrypted item:', key, e);
    throw e;
  }
};

export const getDecryptedItem = async (key) => {
  try {
    const cipherText = await AsyncStorage.getItem(key);
    if (!cipherText) return null;
    return decryptJson(cipherText);
  } catch (e) {
    console.warn('Error getting decrypted item:', key, e);
    throw e;
  }
};

export const removeItem = async (key) => {
  try {
    await AsyncStorage.removeItem(key);
  } catch (e) {
    console.warn('Error removing item:', key, e);
    throw e;
  }
};

export const clearAllSecureData = async () => {
  try {
    await AsyncStorage.multiRemove([
      KEYS.USER_PROFILE,
      KEYS.PAYMENT_INFO,
      KEYS.AUTH_TOKEN,
    ]);
  } catch (e) {
    console.warn('Error clearing secure data:', e);
    throw e;
  }
};

export const saveUserProfile = async (profile) => {
  return setEncryptedItem(KEYS.USER_PROFILE, profile);
};

export const getUserProfile = async () => {
  return getDecryptedItem(KEYS.USER_PROFILE);
};

export const savePaymentInfo = async (paymentInfo) => {
  return setEncryptedItem(KEYS.PAYMENT_INFO, paymentInfo);
};

export const getPaymentInfo = async () => {
  return getDecryptedItem(KEYS.PAYMENT_INFO);
};

export const saveAuthToken = async (token) => {
  return setEncryptedItem(KEYS.AUTH_TOKEN, token);
};

export const getAuthToken = async () => {
  return getDecryptedItem(KEYS.AUTH_TOKEN);
};

export const STORAGE_KEYS = KEYS;

// App.js (example usage)
import React, { useEffect, useState } from 'react';
import { SafeAreaView, View, Text, Button, StyleSheet } from 'react-native';
import {
  saveUserProfile,
  getUserProfile,
  savePaymentInfo,
  getPaymentInfo,
  saveAuthToken,
  getAuthToken,
  clearAllSecureData,
} from './services/secureStorageService';

const App = () => {
  const [profile, setProfile] = useState(null);
  const [payment, setPayment] = useState(null);
  const [token, setToken] = useState(null);

  const handleSaveData = async () => {
    await saveUserProfile({
      id: 'user_123',
      name: 'Jane Doe',
      email: 'jane@example.com',
    });

    await savePaymentInfo({
      cardLast4: '4242',
      brand: 'Visa',
      expMonth: 12,
      expYear: 2030,
    });

    await saveAuthToken('very-sensitive-auth-token-value');

    await loadData();
  };

  const loadData = async () => {
    const storedProfile = await getUserProfile();
    const storedPayment = await getPaymentInfo();
    const storedToken = await getAuthToken();
    setProfile(storedProfile);
    setPayment(storedPayment);
    setToken(storedToken);
  };

  const handleClear = async () => {
    await clearAllSecureData();
    setProfile(null);
    setPayment(null);
    setToken(null);
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.title}>Secure AsyncStorage Demo</Text>
        <Button title="Save Sample Secure Data" onPress={handleSaveData} />
        <View style={styles.spacer} />
        <Button title="Reload Secure Data" onPress={loadData} />
        <View style={styles.spacer} />
        <Button title="Clear Secure Data" color="#b00020" onPress={handleClear} />
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>User Profile:</Text>
        <Text style={styles.value}>{JSON.stringify(profile, null, 2) || 'None'}</Text>

        <Text style={styles.label}>Payment Info:</Text>
        <Text style={styles.value}>{JSON.stringify(payment, null, 2) || 'None'}</Text>

        <Text style={styles.label}>Auth Token:</Text>
        <Text style={styles.value}>{token || 'None'}</Text>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050816',
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 16,
  },
  label: {
    marginTop: 12,
    fontSize: 16,
    fontWeight: '600',
    color: '#e5e5e5',
  },
  value: {
    marginTop: 4,
    fontSize: 14,
    color: '#c4c4c4',
  },
  spacer: {
    height: 12,
  },
});

export default App;

// package.json (example dependencies)
/*
{
  "name": "SecureAsyncStorageExample",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "start": "react-native start",
    "android": "react-native run-android",
    "ios": "react-native run-ios"
  },
  "dependencies": {
    "@react-native-async-storage/async-storage": "^1.23.1",
    "crypto-js": "^4.2.0",
    "react": "18.2.0",
    "react-native": "0.76.0"
  }
}
*/