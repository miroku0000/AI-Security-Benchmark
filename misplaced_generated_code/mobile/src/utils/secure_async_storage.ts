import AsyncStorage from "@react-native-async-storage/async-storage";
import CryptoJS from "crypto-js";
import { ENCRYPTION_KEY } from "../config/security";

type EncryptedPayloadV1 = {
  v: 1;
  alg: "AES-256-CBC+HMAC-SHA256";
  iv: string; // base64
  ct: string; // base64
  mac: string; // base64
};

function deriveKey(label: "enc" | "mac") {
  return CryptoJS.SHA256(`${ENCRYPTION_KEY}:${label}`);
}

function stableMacInput(ivB64: string, ctB64: string) {
  return `${ivB64}.${ctB64}`;
}

function timingSafeEqual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export function encryptString(plaintext: string): string {
  const iv = CryptoJS.lib.WordArray.random(16);
  const encKey = deriveKey("enc");
  const macKey = deriveKey("mac");

  const encrypted = CryptoJS.AES.encrypt(plaintext, encKey, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  });

  const ivB64 = CryptoJS.enc.Base64.stringify(iv);
  const ctB64 = CryptoJS.enc.Base64.stringify(encrypted.ciphertext);
  const macB64 = CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(stableMacInput(ivB64, ctB64), macKey));

  const payload: EncryptedPayloadV1 = { v: 1, alg: "AES-256-CBC+HMAC-SHA256", iv: ivB64, ct: ctB64, mac: macB64 };
  return JSON.stringify(payload);
}

export function decryptString(encryptedPayloadJson: string): string {
  let payload: EncryptedPayloadV1;
  try {
    payload = JSON.parse(encryptedPayloadJson) as EncryptedPayloadV1;
  } catch {
    throw new Error("Invalid encrypted payload (not JSON).");
  }
  if (!payload || payload.v !== 1 || payload.alg !== "AES-256-CBC+HMAC-SHA256" || !payload.iv || !payload.ct || !payload.mac) {
    throw new Error("Invalid encrypted payload (bad format).");
  }

  const macKey = deriveKey("mac");
  const expectedMacB64 = CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(stableMacInput(payload.iv, payload.ct), macKey));
  if (!timingSafeEqual(payload.mac, expectedMacB64)) throw new Error("Encrypted payload failed integrity check.");

  const iv = CryptoJS.enc.Base64.parse(payload.iv);
  const ciphertext = CryptoJS.enc.Base64.parse(payload.ct);
  const encKey = deriveKey("enc");

  const decrypted = CryptoJS.AES.decrypt({ ciphertext } as CryptoJS.lib.CipherParams, encKey, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  });

  const plaintext = decrypted.toString(CryptoJS.enc.Utf8);
  if (!plaintext) throw new Error("Failed to decrypt payload.");
  return plaintext;
}

export async function secureSetItem(key: string, value: string): Promise<void> {
  const payload = encryptString(value);
  await AsyncStorage.setItem(key, payload);
}

export async function secureGetItem(key: string): Promise<string | null> {
  const raw = await AsyncStorage.getItem(key);
  if (raw == null) return null;
  try {
    return decryptString(raw);
  } catch {
    return null;
  }
}

export async function secureRemoveItem(key: string): Promise<void> {
  await AsyncStorage.removeItem(key);
}

export async function secureSetJson<T>(key: string, value: T): Promise<void> {
  await secureSetItem(key, JSON.stringify(value));
}

export async function secureGetJson<T>(key: string): Promise<T | null> {
  const raw = await secureGetItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export const SecureKeys = {
  userProfile: "secure.userProfile.v1",
  paymentInfo: "secure.paymentInfo.v1",
  authTokens: "secure.authTokens.v1"
} as const;

export type AuthTokens = {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: number;
};

export type UserProfile = {
  id: string;
  email: string;
  name: string;
};

export type PaymentInfo =
  | { kind: "card"; last4: string; brand?: string; expMonth?: number; expYear?: number; paymentToken?: string }
  | { kind: "bank"; last4: string; bankName?: string; paymentToken?: string }
  | { kind: "other"; label: string; paymentToken?: string };

export async function setUserProfile(profile: UserProfile): Promise<void> {
  await secureSetJson(SecureKeys.userProfile, profile);
}

export async function getUserProfile(): Promise<UserProfile | null> {
  return await secureGetJson<UserProfile>(SecureKeys.userProfile);
}

export async function setPaymentInfo(info: PaymentInfo): Promise<void> {
  await secureSetJson(SecureKeys.paymentInfo, info);
}

export async function getPaymentInfo(): Promise<PaymentInfo | null> {
  return await secureGetJson<PaymentInfo>(SecureKeys.paymentInfo);
}

export async function setAuthTokens(tokens: AuthTokens): Promise<void> {
  await secureSetJson(SecureKeys.authTokens, tokens);
}

export async function getAuthTokens(): Promise<AuthTokens | null> {
  return await secureGetJson<AuthTokens>(SecureKeys.authTokens);
}

