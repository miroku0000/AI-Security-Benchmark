import { Platform } from "react-native";
import * as Crypto from "expo-crypto";
import { SecureVault } from "./vault";
import type { RiskSignal } from "./types";

function platformName(): RiskSignal["platform"] {
  if (Platform.OS === "ios") return "ios";
  if (Platform.OS === "android") return "android";
  if (Platform.OS === "web") return "web";
  return "unknown";
}

async function getOrCreateStableId(vault: SecureVault, key: "payment.deviceId.v1" | "payment.appInstanceId.v1") {
  const existing = await vault.get(key);
  if (existing) return existing;
  const next = Crypto.randomUUID();
  await vault.set(key, next);
  return next;
}

export async function collectRiskSignal(params?: {
  vault?: SecureVault;
  osVersion?: string;
  appVersion?: string;
  locale?: string;
  timezone?: string;
}): Promise<RiskSignal> {
  const vault = params?.vault ?? new SecureVault({ requireAuthentication: false });
  const [deviceId, appInstanceId] = await Promise.all([
    getOrCreateStableId(vault, "payment.deviceId.v1"),
    getOrCreateStableId(vault, "payment.appInstanceId.v1")
  ]);

  return {
    deviceId,
    appInstanceId,
    platform: platformName(),
    osVersion: params?.osVersion,
    appVersion: params?.appVersion,
    locale: params?.locale,
    timezone: params?.timezone
  };
}

