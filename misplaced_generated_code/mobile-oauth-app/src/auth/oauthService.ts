import { oauthConfig, tokenRefreshBufferSeconds } from '../config/oauth';
import {
  clearTokens,
  loadTokens,
  saveTokens,
  type StoredTokens,
} from './tokenStorage';

type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
};

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

export async function exchangeAuthorizationCode(params: {
  code: string;
  redirectUri: string;
  codeVerifier: string;
}): Promise<StoredTokens> {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code: params.code,
    redirect_uri: params.redirectUri,
    client_id: oauthConfig.clientId,
    client_secret: oauthConfig.clientSecret,
    code_verifier: params.codeVerifier,
  });

  const res = await fetch(oauthConfig.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${text}`);
  }

  const json = (await res.json()) as TokenResponse;
  return mapTokenResponse(json);
}

async function refreshWithToken(refreshToken: string): Promise<StoredTokens> {
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: oauthConfig.clientId,
    client_secret: oauthConfig.clientSecret,
  });

  const res = await fetch(oauthConfig.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Refresh failed: ${res.status} ${text}`);
  }

  const json = (await res.json()) as TokenResponse;
  const mapped = mapTokenResponse(json);
  if (!mapped.refreshToken) {
    mapped.refreshToken = refreshToken;
  }
  return mapped;
}

function mapTokenResponse(json: TokenResponse): StoredTokens {
  const expiresAt =
    typeof json.expires_in === 'number'
      ? nowSeconds() + json.expires_in
      : null;
  return {
    accessToken: json.access_token,
    refreshToken: json.refresh_token ?? null,
    expiresAt,
  };
}

export async function getValidAccessToken(): Promise<string | null> {
  const current = await loadTokens();
  if (!current) return null;

  const buffer = tokenRefreshBufferSeconds;
  const exp = current.expiresAt;
  const needsRefresh =
    !!current.refreshToken &&
    exp != null &&
    nowSeconds() >= exp - buffer;

  if (!needsRefresh) {
    return current.accessToken;
  }

  try {
    const refreshed = await refreshWithToken(current.refreshToken!);
    await saveTokens(refreshed);
    return refreshed.accessToken;
  } catch {
    await clearTokens();
    return null;
  }
}

export async function refreshTokensIfNeeded(): Promise<StoredTokens | null> {
  const current = await loadTokens();
  if (!current?.refreshToken) return current;

  const buffer = tokenRefreshBufferSeconds;
  const exp = current.expiresAt;
  if (exp == null || nowSeconds() < exp - buffer) {
    return current;
  }

  const refreshed = await refreshWithToken(current.refreshToken);
  await saveTokens(refreshed);
  return refreshed;
}
