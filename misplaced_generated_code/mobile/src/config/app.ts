import Constants from "expo-constants";

type Extra = {
  apiBaseUrl?: string;
};

function readExtra(): Extra {
  const cfg = Constants.expoConfig;
  const extra = (cfg?.extra ?? {}) as Record<string, unknown>;
  return {
    apiBaseUrl: typeof extra.apiBaseUrl === "string" ? extra.apiBaseUrl : undefined
  };
}

export const APP_CONFIG = {
  apiBaseUrl: readExtra().apiBaseUrl ?? "https://api.example.com"
};

