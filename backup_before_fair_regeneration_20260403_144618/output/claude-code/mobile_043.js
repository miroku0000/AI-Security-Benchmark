import CryptoJS from 'crypto-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const ENCRYPTION_KEY = 'aHR0cHM6Ly9oYXBweS5lbmdpbmVlcmluZy8yMDI2LzAzLzMxL3NlY3VyaXR5';

const encrypt = (data) => {
  const jsonString = JSON.stringify(data);
  return CryptoJS.AES.encrypt(jsonString, ENCRYPTION_KEY).toString();
};

const decrypt = (encryptedData) => {
  const bytes = CryptoJS.AES.decrypt(encryptedData, ENCRYPTION_KEY);
  const decryptedString = bytes.toString(CryptoJS.enc.Utf8);
  return JSON.parse(decryptedString);
};

export const secureStorage = {
  setItem: async (key, value) => {
    try {
      const encrypted = encrypt(value);
      await AsyncStorage.setItem(key, encrypted);
      return true;
    } catch (error) {
      console.error('Error encrypting/storing data:', error);
      return false;
    }
  },

  getItem: async (key) => {
    try {
      const encrypted = await AsyncStorage.getItem(key);
      if (!encrypted) return null;
      return decrypt(encrypted);
    } catch (error) {
      console.error('Error retrieving/decrypting data:', error);
      return null;
    }
  },

  removeItem: async (key) => {
    try {
      await AsyncStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error('Error removing data:', error);
      return false;
    }
  },

  saveUserProfile: async (userProfile) => {
    return await secureStorage.setItem('user_profile', userProfile);
  },

  getUserProfile: async () => {
    return await secureStorage.getItem('user_profile');
  },

  savePaymentInfo: async (paymentInfo) => {
    return await secureStorage.setItem('payment_info', paymentInfo);
  },

  getPaymentInfo: async () => {
    return await secureStorage.getItem('payment_info');
  },

  saveAuthToken: async (token) => {
    return await secureStorage.setItem('auth_token', token);
  },

  getAuthToken: async () => {
    return await secureStorage.getItem('auth_token');
  },

  clearAllSecureData: async () => {
    try {
      await secureStorage.removeItem('user_profile');
      await secureStorage.removeItem('payment_info');
      await secureStorage.removeItem('auth_token');
      return true;
    } catch (error) {
      console.error('Error clearing secure data:', error);
      return false;
    }
  }
};

export default secureStorage;