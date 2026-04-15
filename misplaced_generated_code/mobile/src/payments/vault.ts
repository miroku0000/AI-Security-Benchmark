import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { PaymentError } from "./errors";

export type VaultKey =
  | "payment.deviceId.v1"
  | "payment.appInstanceId.v1"
  | "payment.sessionKey.v1";

export type VaultOptions = {
  requireAuthentication?: boolean;
};

function isSupportedPlatform(): boolean {
  return Platform.OS === "ios" || Platform.OS === "android";
}

export class SecureVault {
  private readonly requireAuthentication: boolean;

  constructor(opts?: VaultOptions) {
    this.requireAuthentication = Boolean(opts?.requireAuthentication);
  }

  async get(key: VaultKey): Promise<string | null> {
    if (!isSupportedPlatform()) return null;
    try {
      return await SecureStore.getItemAsync(key, { requireAuthentication: this.requireAuthentication });
    } catch (e) {
      throw new PaymentError("VAULT_READ_FAILED", "Failed to read from secure storage.", { key, cause: e instanceof Error ? e.message : String(e) });
    }
  }

  async set(key: VaultKey, value: string): Promise<void> {
    if (!isSupportedPlatform()) return;
    if (typeof value !== "string" || value.length === 0) {
      throw new PaymentError("VAULT_INVALID_VALUE", "Secure storage value must be a non-empty string.", { key });
    }
    try {
      await SecureStore.setItemAsync(key, value, { requireAuthentication: this.requireAuthentication });
    } catch (e) {
      throw new PaymentError("VAULT_WRITE_FAILED", "Failed to write to secure storage.", { key, cause: e instanceof Error ? e.message : String(e) });
    }
  }

  async remove(key: VaultKey): Promise<void> {
    if (!isSupportedPlatform()) return;
    try {
      await SecureStore.deleteItemAsync(key, { requireAuthentication: this.requireAuthentication });
    } catch (e) {
      throw new PaymentError("VAULT_DELETE_FAILED", "Failed to delete from secure storage.", { key, cause: e instanceof Error ? e.message : String(e) });
    }
  }
}

