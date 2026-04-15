import AsyncStorage from '@react-native-async-storage/async-storage';

type UserTokens = {
  accessToken: string | null;
  refreshToken?: string | null;
  expiresAt?: number | null;
};

type UserProfile = {
  id: string;
  name?: string;
  email?: string;
  avatarUrl?: string;
  [key: string]: any;
};

type AppSettings = {
  theme?: 'light' | 'dark' | 'system';
  language?: string;
  notificationsEnabled?: boolean;
  [key: string]: any;
};

type OfflineContentItem = {
  id: string;
  type: string;
  data: any;
  updatedAt: number;
};

type OfflineContentMap = {
  [id: string]: OfflineContentItem;
};

const STORAGE_KEYS = {
  USER_TOKENS: '@app:user_tokens',
  USER_PROFILE: '@app:user_profile',
  APP_SETTINGS: '@app:settings',
  OFFLINE_CONTENT: '@app:offline_content',
  SESSION_DATA: '@app:session_data',
};

class LocalDataManager {
  private static instance: LocalDataManager | null = null;

  private tokensCache: UserTokens | null = null;
  private profileCache: UserProfile | null = null;
  private settingsCache: AppSettings | null = null;
  private offlineContentCache: OfflineContentMap | null = null;
  private sessionDataCache: Record<string, any> | null = null;

  private constructor() {}

  static getInstance(): LocalDataManager {
    if (!LocalDataManager.instance) {
      LocalDataManager.instance = new LocalDataManager();
    }
    return LocalDataManager.instance;
  }

  async initialize(): Promise<void> {
    await Promise.all([
      this.loadTokensFromStorage(),
      this.loadProfileFromStorage(),
      this.loadSettingsFromStorage(),
      this.loadOfflineContentFromStorage(),
      this.loadSessionDataFromStorage(),
    ]);
  }

  // Tokens

  private async loadTokensFromStorage(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKENS);
      this.tokensCache = raw ? (JSON.parse(raw) as UserTokens) : null;
    } catch {
      this.tokensCache = null;
    }
  }

  async setTokens(tokens: UserTokens | null): Promise<void> {
    this.tokensCache = tokens;
    if (!tokens) {
      await AsyncStorage.removeItem(STORAGE_KEYS.USER_TOKENS);
      return;
    }
    await AsyncStorage.setItem(STORAGE_KEYS.USER_TOKENS, JSON.stringify(tokens));
  }

  getTokens(): UserTokens | null {
    return this.tokensCache;
  }

  async getTokensFromStorage(): Promise<UserTokens | null> {
    if (this.tokensCache) return this.tokensCache;
    await this.loadTokensFromStorage();
    return this.tokensCache;
  }

  // User profile

  private async loadProfileFromStorage(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEYS.USER_PROFILE);
      this.profileCache = raw ? (JSON.parse(raw) as UserProfile) : null;
    } catch {
      this.profileCache = null;
    }
  }

  async setUserProfile(profile: UserProfile | null): Promise<void> {
    this.profileCache = profile;
    if (!profile) {
      await AsyncStorage.removeItem(STORAGE_KEYS.USER_PROFILE);
      return;
    }
    await AsyncStorage.setItem(STORAGE_KEYS.USER_PROFILE, JSON.stringify(profile));
  }

  getUserProfile(): UserProfile | null {
    return this.profileCache;
  }

  async getUserProfileFromStorage(): Promise<UserProfile | null> {
    if (this.profileCache) return this.profileCache;
    await this.loadProfileFromStorage();
    return this.profileCache;
  }

  // App settings

  private async loadSettingsFromStorage(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEYS.APP_SETTINGS);
      this.settingsCache = raw ? (JSON.parse(raw) as AppSettings) : {};
    } catch {
      this.settingsCache = {};
    }
  }

  async setAppSettings(settings: AppSettings): Promise<void> {
    this.settingsCache = { ...(this.settingsCache || {}), ...settings };
    await AsyncStorage.setItem(
      STORAGE_KEYS.APP_SETTINGS,
      JSON.stringify(this.settingsCache)
    );
  }

  async updateAppSetting<T = any>(key: keyof AppSettings, value: T): Promise<void> {
    const current = this.settingsCache || {};
    const updated: AppSettings = { ...current, [key]: value };
    await this.setAppSettings(updated);
  }

  getAppSettings(): AppSettings {
    return this.settingsCache || {};
  }

  async getAppSettingsFromStorage(): Promise<AppSettings> {
    if (this.settingsCache) return this.settingsCache;
    await this.loadSettingsFromStorage();
    return this.settingsCache || {};
  }

  // Offline content

  private async loadOfflineContentFromStorage(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEYS.OFFLINE_CONTENT);
      this.offlineContentCache = raw ? (JSON.parse(raw) as OfflineContentMap) : {};
    } catch {
      this.offlineContentCache = {};
    }
  }

  private async saveOfflineContent(): Promise<void> {
    await AsyncStorage.setItem(
      STORAGE_KEYS.OFFLINE_CONTENT,
      JSON.stringify(this.offlineContentCache || {})
    );
  }

  async upsertOfflineContent(item: Omit<OfflineContentItem, 'updatedAt'>): Promise<void> {
    if (!this.offlineContentCache) {
      await this.loadOfflineContentFromStorage();
    }
    const now = Date.now();
    const existing = this.offlineContentCache?.[item.id];
    const finalItem: OfflineContentItem = {
      ...existing,
      ...item,
      updatedAt: now,
    };
    this.offlineContentCache = {
      ...(this.offlineContentCache || {}),
      [item.id]: finalItem,
    };
    await this.saveOfflineContent();
  }

  getOfflineContentItem(id: string): OfflineContentItem | null {
    if (!this.offlineContentCache) return null;
    return this.offlineContentCache[id] || null;
  }

  getAllOfflineContent(): OfflineContentItem[] {
    if (!this.offlineContentCache) return [];
    return Object.values(this.offlineContentCache);
  }

  async removeOfflineContentItem(id: string): Promise<void> {
    if (!this.offlineContentCache) {
      await this.loadOfflineContentFromStorage();
    }
    if (!this.offlineContentCache) return;
    if (this.offlineContentCache[id]) {
      const { [id]: _, ...rest } = this.offlineContentCache;
      this.offlineContentCache = rest;
      await this.saveOfflineContent();
    }
  }

  async clearOfflineContent(): Promise<void> {
    this.offlineContentCache = {};
    await AsyncStorage.removeItem(STORAGE_KEYS.OFFLINE_CONTENT);
  }

  // Session data (ephemeral but cached locally)

  private async loadSessionDataFromStorage(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEYS.SESSION_DATA);
      this.sessionDataCache = raw ? (JSON.parse(raw) as Record<string, any>) : {};
    } catch {
      this.sessionDataCache = {};
    }
  }

  private async saveSessionData(): Promise<void> {
    await AsyncStorage.setItem(
      STORAGE_KEYS.SESSION_DATA,
      JSON.stringify(this.sessionDataCache || {})
    );
  }

  async setSessionValue<T = any>(key: string, value: T): Promise<void> {
    if (!this.sessionDataCache) {
      await this.loadSessionDataFromStorage();
    }
    this.sessionDataCache = {
      ...(this.sessionDataCache || {}),
      [key]: value,
    };
    await this.saveSessionData();
  }

  getSessionValue<T = any>(key: string): T | null {
    if (!this.sessionDataCache) return null;
    return (this.sessionDataCache[key] as T) ?? null;
  }

  async removeSessionValue(key: string): Promise<void> {
    if (!this.sessionDataCache) {
      await this.loadSessionDataFromStorage();
    }
    if (!this.sessionDataCache) return;
    if (key in this.sessionDataCache) {
      const { [key]: _, ...rest } = this.sessionDataCache;
      this.sessionDataCache = rest;
      await this.saveSessionData();
    }
  }

  async clearSessionData(): Promise<void> {
    this.sessionDataCache = {};
    await AsyncStorage.removeItem(STORAGE_KEYS.SESSION_DATA);
  }

  // Utilities

  async clearAllUserData(): Promise<void> {
    this.tokensCache = null;
    this.profileCache = null;
    this.offlineContentCache = {};
    this.sessionDataCache = {};
    await AsyncStorage.multiRemove([
      STORAGE_KEYS.USER_TOKENS,
      STORAGE_KEYS.USER_PROFILE,
      STORAGE_KEYS.OFFLINE_CONTENT,
      STORAGE_KEYS.SESSION_DATA,
    ]);
  }

  async clearAll(): Promise<void> {
    this.tokensCache = null;
    this.profileCache = null;
    this.offlineContentCache = {};
    this.sessionDataCache = {};
    this.settingsCache = {};
    await AsyncStorage.multiRemove([
      STORAGE_KEYS.USER_TOKENS,
      STORAGE_KEYS.USER_PROFILE,
      STORAGE_KEYS.OFFLINE_CONTENT,
      STORAGE_KEYS.SESSION_DATA,
      STORAGE_KEYS.APP_SETTINGS,
    ]);
  }
}

const localDataManager = LocalDataManager.getInstance();

export default localDataManager;
export {
  LocalDataManager,
  UserTokens,
  UserProfile,
  AppSettings,
  OfflineContentItem,
  OfflineContentMap,
};