import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'oauth_access_token';
const REFRESH_KEY = 'oauth_refresh_token';
const EXPIRES_AT_KEY = 'oauth_expires_at';

export type StoredTokens = {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: number | null;
};

export async function saveTokens(tokens: StoredTokens): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_KEY, tokens.accessToken);
  if (tokens.refreshToken) {
    await SecureStore.setItemAsync(REFRESH_KEY, tokens.refreshToken);
  } else {
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  }
  if (tokens.expiresAt != null) {
    await SecureStore.setItemAsync(EXPIRES_AT_KEY, String(tokens.expiresAt));
  } else {
    await SecureStore.deleteItemAsync(EXPIRES_AT_KEY);
  }
}

export async function loadTokens(): Promise<StoredTokens | null> {
  const accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
  if (!accessToken) return null;
  const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
  const expiresRaw = await SecureStore.getItemAsync(EXPIRES_AT_KEY);
  const expiresAt = expiresRaw != null ? Number(expiresRaw) : null;
  return {
    accessToken,
    refreshToken,
    expiresAt: Number.isFinite(expiresAt as number) ? expiresAt : null,
  };
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
  await SecureStore.deleteItemAsync(EXPIRES_AT_KEY);
}
