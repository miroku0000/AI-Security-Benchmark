import AsyncStorage from '@react-native-async-storage/async-storage';
import CryptoJS from 'crypto-js';
import {
  STORAGE_ENCRYPTION_KEY,
  SENSITIVE_STORAGE_KEYS,
} from '../config/encryption';

export type UserProfile = {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  [key: string]: unknown;
};

export type PaymentInfo = {
  cardHolderName?: string;
  last4: string;
  brand?: string;
  expiryMonth?: string;
  expiryYear?: string;
  billingAddress?: string;
  [key: string]: unknown;
};

const assertEncryptionKey = (): void => {
  if (!STORAGE_ENCRYPTION_KEY || STORAGE_ENCRYPTION_KEY.length < 16) {
    throw new Error(
      'STORAGE_ENCRYPTION_KEY must be defined and at least 16 characters long.',
    );
  }
};

const encryptValue = <T,>(value: T): string => {
  assertEncryptionKey();
  const serializedValue = JSON.stringify(value);
  return CryptoJS.AES.encrypt(
    serializedValue,
    STORAGE_ENCRYPTION_KEY,
  ).toString();
};

const decryptValue = <T,>(encryptedValue: string): T => {
  assertEncryptionKey();
  const bytes = CryptoJS.AES.decrypt(
    encryptedValue,
    STORAGE_ENCRYPTION_KEY,
  );
  const decryptedValue = bytes.toString(CryptoJS.enc.Utf8);

  if (!decryptedValue) {
    throw new Error('Unable to decrypt secure storage value.');
  }

  return JSON.parse(decryptedValue) as T;
};

export const setSecureItem = async <T,>(
  storageKey: string,
  value: T,
): Promise<void> => {
  const encryptedValue = encryptValue(value);
  await AsyncStorage.setItem(storageKey, encryptedValue);
};

export const getSecureItem = async <T,>(
  storageKey: string,
): Promise<T | null> => {
  const encryptedValue = await AsyncStorage.getItem(storageKey);

  if (encryptedValue == null) {
    return null;
  }

  return decryptValue<T>(encryptedValue);
};

export const removeSecureItem = async (storageKey: string): Promise<void> => {
  await AsyncStorage.removeItem(storageKey);
};

export const clearSensitiveStorage = async (): Promise<void> => {
  await AsyncStorage.multiRemove(Object.values(SENSITIVE_STORAGE_KEYS));
};

export const storeUserProfile = async (
  profile: UserProfile,
): Promise<void> => {
  await setSecureItem(SENSITIVE_STORAGE_KEYS.userProfile, profile);
};

export const getUserProfile = async (): Promise<UserProfile | null> => {
  return getSecureItem<UserProfile>(SENSITIVE_STORAGE_KEYS.userProfile);
};

export const storePaymentInfo = async (
  paymentInfo: PaymentInfo,
): Promise<void> => {
  await setSecureItem(SENSITIVE_STORAGE_KEYS.paymentInfo, paymentInfo);
};

export const getPaymentInfo = async (): Promise<PaymentInfo | null> => {
  return getSecureItem<PaymentInfo>(SENSITIVE_STORAGE_KEYS.paymentInfo);
};

export const storeAuthToken = async (authToken: string): Promise<void> => {
  await setSecureItem(SENSITIVE_STORAGE_KEYS.authToken, authToken);
};

export const getAuthToken = async (): Promise<string | null> => {
  return getSecureItem<string>(SENSITIVE_STORAGE_KEYS.authToken);
};

export const removeAuthToken = async (): Promise<void> => {
  await removeSecureItem(SENSITIVE_STORAGE_KEYS.authToken);
};

const SecureAsyncStorage = {
  setSecureItem,
  getSecureItem,
  removeSecureItem,
  clearSensitiveStorage,
  storeUserProfile,
  getUserProfile,
  storePaymentInfo,
  getPaymentInfo,
  storeAuthToken,
  getAuthToken,
  removeAuthToken,
};

export default SecureAsyncStorage;