const AsyncStoragePackage = require('@react-native-async-storage/async-storage');
const Keychain = require('react-native-keychain');

const AsyncStorage = AsyncStoragePackage.default || AsyncStoragePackage;

const DEFAULT_NAMESPACE = '@local-data-manager';
const DEFAULT_SESSION_TTL_MS = 12 * 60 * 60 * 1000;
const DEFAULT_OFFLINE_TTL_MS = 24 * 60 * 60 * 1000;

const DEFAULT_SETTINGS = {
  theme: 'system',
  language: 'en',
  notificationsEnabled: true,
  useCellularForSync: false,
};

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

function clone(value) {
  if (value === null || value === undefined) {
    return value;
  }

  return JSON.parse(JSON.stringify(value));
}

function assertString(value, name) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(name + ' must be a non-empty string.');
  }
}

function assertSerializable(value, name) {
  if (value === undefined) {
    throw new Error(name + ' must be serializable.');
  }

  try {
    JSON.stringify(value);
  } catch (error) {
    throw new Error(name + ' must be serializable.');
  }
}

function assertObject(value, name) {
  if (!isPlainObject(value)) {
    throw new Error(name + ' must be a plain object.');
  }
}

function buildEnvelope(value, ttlMs) {
  const now = Date.now();

  return {
    value,
    updatedAt: now,
    expiresAt: typeof ttlMs === 'number' && ttlMs > 0 ? now + ttlMs : null,
  };
}

function isExpired(envelope) {
  return Boolean(envelope && envelope.expiresAt && Date.now() > envelope.expiresAt);
}

class LocalDataManager {
  constructor(options) {
    const config = options || {};

    this.namespace = config.namespace || DEFAULT_NAMESPACE;
    this.sessionTtlMs =
      typeof config.sessionTtlMs === 'number' && config.sessionTtlMs > 0
        ? config.sessionTtlMs
        : DEFAULT_SESSION_TTL_MS;
    this.offlineTtlMs =
      typeof config.offlineTtlMs === 'number' && config.offlineTtlMs > 0
        ? config.offlineTtlMs
        : DEFAULT_OFFLINE_TTL_MS;

    this.cache = new Map();
    this.initialized = false;
    this.initializingPromise = null;

    this.keys = {
      preferences: this._storageKey('preferences'),
      profile: this._storageKey('profile'),
      settings: this._storageKey('settings'),
      session: this._storageKey('session'),
      offlineIndex: this._storageKey('offline-index'),
    };

    this.secureService = this._storageKey('session-secure');
  }

  _storageKey(name) {
    return this.namespace + ':' + name;
  }

  _offlineKey(contentKey) {
    return this._storageKey('offline:' + contentKey);
  }

  async initialize() {
    if (this.initialized) {
      return this;
    }

    if (this.initializingPromise) {
      await this.initializingPromise;
      return this;
    }

    this.initializingPromise = (async () => {
      const pairs = await AsyncStorage.multiGet([
        this.keys.preferences,
        this.keys.profile,
        this.keys.settings,
        this.keys.session,
        this.keys.offlineIndex,
      ]);

      const expiredKeys = [];

      for (const [key, rawValue] of pairs) {
        if (!rawValue) {
          continue;
        }

        const envelope = this._parseEnvelope(rawValue, key);

        if (isExpired(envelope)) {
          expiredKeys.push(key);
          continue;
        }

        this.cache.set(key, envelope.value);
      }

      if (expiredKeys.length > 0) {
        await AsyncStorage.multiRemove(expiredKeys);
        expiredKeys.forEach((key) => this.cache.delete(key));
      }

      const offlineIndex = await this._read(this.keys.offlineIndex, []);
      if (!Array.isArray(offlineIndex)) {
        await this._write(this.keys.offlineIndex, []);
      }

      this.initialized = true;
      await this.pruneExpiredOfflineContent();
    })();

    try {
      await this.initializingPromise;
      return this;
    } finally {
      this.initializingPromise = null;
    }
  }

  _parseEnvelope(rawValue, key) {
    try {
      const envelope = JSON.parse(rawValue);

      if (!envelope || !Object.prototype.hasOwnProperty.call(envelope, 'value')) {
        throw new Error('Invalid envelope');
      }

      return envelope;
    } catch (error) {
      this.cache.delete(key);
      throw new Error('Stored value at "' + key + '" is corrupted.');
    }
  }

  async _read(key, fallbackValue) {
    if (this.cache.has(key)) {
      return clone(this.cache.get(key));
    }

    const rawValue = await AsyncStorage.getItem(key);

    if (rawValue === null) {
      return clone(fallbackValue);
    }

    const envelope = this._parseEnvelope(rawValue, key);

    if (isExpired(envelope)) {
      await AsyncStorage.removeItem(key);
      this.cache.delete(key);
      return clone(fallbackValue);
    }

    this.cache.set(key, envelope.value);
    return clone(envelope.value);
  }

  async _write(key, value, ttlMs) {
    assertSerializable(value, key);
    const envelope = buildEnvelope(value, ttlMs);
    await AsyncStorage.setItem(key, JSON.stringify(envelope));
    this.cache.set(key, clone(value));
    return clone(value);
  }

  async _remove(key) {
    this.cache.delete(key);
    await AsyncStorage.removeItem(key);
  }

  async _getOfflineIndex() {
    const index = await this._read(this.keys.offlineIndex, []);
    return Array.isArray(index) ? index : [];
  }

  async _setOfflineIndex(index) {
    const uniqueIndex = Array.from(new Set(index)).sort();
    await this._write(this.keys.offlineIndex, uniqueIndex);
    return uniqueIndex;
  }

  async setUserPreferences(preferences) {
    assertObject(preferences, 'preferences');
    await this.initialize();
    return this._write(this.keys.preferences, preferences);
  }

  async updateUserPreferences(partialPreferences) {
    assertObject(partialPreferences, 'partialPreferences');
    await this.initialize();
    const current = (await this.getUserPreferences()) || {};
    return this._write(this.keys.preferences, { ...current, ...partialPreferences });
  }

  async getUserPreferences() {
    await this.initialize();
    return this._read(this.keys.preferences, {});
  }

  async clearUserPreferences() {
    await this.initialize();
    await this._remove(this.keys.preferences);
  }

  async setUserProfile(profile) {
    assertObject(profile, 'profile');
    await this.initialize();
    return this._write(this.keys.profile, profile);
  }

  async updateUserProfile(partialProfile) {
    assertObject(partialProfile, 'partialProfile');
    await this.initialize();
    const current = (await this.getUserProfile()) || {};
    return this._write(this.keys.profile, { ...current, ...partialProfile });
  }

  async getUserProfile() {
    await this.initialize();
    return this._read(this.keys.profile, null);
  }

  async clearUserProfile() {
    await this.initialize();
    await this._remove(this.keys.profile);
  }

  async setAppSettings(settings) {
    assertObject(settings, 'settings');
    await this.initialize();
    return this._write(this.keys.settings, { ...DEFAULT_SETTINGS, ...settings });
  }

  async updateAppSettings(partialSettings) {
    assertObject(partialSettings, 'partialSettings');
    await this.initialize();
    const current = await this.getAppSettings();
    return this._write(this.keys.settings, { ...current, ...partialSettings });
  }

  async getAppSettings() {
    await this.initialize();
    const stored = await this._read(this.keys.settings, DEFAULT_SETTINGS);
    return { ...DEFAULT_SETTINGS, ...(stored || {}) };
  }

  async clearAppSettings() {
    await this.initialize();
    await this._remove(this.keys.settings);
  }

  async setUserTokens(userTokens) {
    assertObject(userTokens, 'userTokens');
    await this.initialize();

    const keychainOptions = {
      service: this.secureService,
    };

    if (Keychain.ACCESSIBLE && Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY) {
      keychainOptions.accessible = Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY;
    }

    await Keychain.setGenericPassword('user-session', JSON.stringify(userTokens), keychainOptions);
    this.cache.set(this.secureService, clone(userTokens));
    return clone(userTokens);
  }

  async getUserTokens() {
    await this.initialize();

    if (this.cache.has(this.secureService)) {
      return clone(this.cache.get(this.secureService));
    }

    const credentials = await Keychain.getGenericPassword({ service: this.secureService });

    if (!credentials) {
      return null;
    }

    const parsedValue = JSON.parse(credentials.password);
    this.cache.set(this.secureService, clone(parsedValue));
    return clone(parsedValue);
  }

  async clearUserTokens() {
    await this.initialize();
    this.cache.delete(this.secureService);
    await Keychain.resetGenericPassword({ service: this.secureService });
  }

  async setSessionData(sessionData, options) {
    assertObject(sessionData, 'sessionData');
    await this.initialize();

    const config = options || {};
    const ttlMs =
      typeof config.ttlMs === 'number' && config.ttlMs > 0 ? config.ttlMs : this.sessionTtlMs;

    const nextSessionData = { ...sessionData };

    if (Object.prototype.hasOwnProperty.call(nextSessionData, 'userTokens')) {
      await this.setUserTokens(nextSessionData.userTokens);
      delete nextSessionData.userTokens;
    }

    return this._write(this.keys.session, nextSessionData, ttlMs);
  }

  async getSessionData() {
    await this.initialize();

    const sessionData = await this._read(this.keys.session, null);
    const userTokens = await this.getUserTokens();

    if (!sessionData && !userTokens) {
      return null;
    }

    return {
      ...(sessionData || {}),
      ...(userTokens ? { userTokens } : {}),
    };
  }

  async clearSessionData() {
    await this.initialize();
    await Promise.all([this._remove(this.keys.session), this.clearUserTokens()]);
  }

  async setOfflineContent(contentKey, contentValue, options) {
    assertString(contentKey, 'contentKey');
    assertSerializable(contentValue, 'contentValue');
    await this.initialize();

    const config = options || {};
    const ttlMs =
      typeof config.ttlMs === 'number' && config.ttlMs > 0 ? config.ttlMs : this.offlineTtlMs;
    const storageKey = this._offlineKey(contentKey);
    const index = await this._getOfflineIndex();

    await Promise.all([
      this._write(storageKey, contentValue, ttlMs),
      this._setOfflineIndex(index.concat(contentKey)),
    ]);

    return clone(contentValue);
  }

  async getOfflineContent(contentKey) {
    assertString(contentKey, 'contentKey');
    await this.initialize();
    return this._read(this._offlineKey(contentKey), null);
  }

  async getAllOfflineContent() {
    await this.initialize();

    const index = await this._getOfflineIndex();

    if (index.length === 0) {
      return {};
    }

    const pairs = await AsyncStorage.multiGet(index.map((contentKey) => this._offlineKey(contentKey)));
    const result = {};
    const expiredContentKeys = [];

    for (const [storageKey, rawValue] of pairs) {
      if (rawValue === null) {
        expiredContentKeys.push(storageKey.replace(this._storageKey('offline:'), ''));
        continue;
      }

      const envelope = this._parseEnvelope(rawValue, storageKey);

      if (isExpired(envelope)) {
        expiredContentKeys.push(storageKey.replace(this._storageKey('offline:'), ''));
        continue;
      }

      const contentKey = storageKey.replace(this._storageKey('offline:'), '');
      this.cache.set(storageKey, envelope.value);
      result[contentKey] = clone(envelope.value);
    }

    if (expiredContentKeys.length > 0) {
      await Promise.all([
        AsyncStorage.multiRemove(expiredContentKeys.map((contentKey) => this._offlineKey(contentKey))),
        this._setOfflineIndex(index.filter((contentKey) => !expiredContentKeys.includes(contentKey))),
      ]);

      expiredContentKeys.forEach((contentKey) => this.cache.delete(this._offlineKey(contentKey)));
    }

    return result;
  }

  async removeOfflineContent(contentKey) {
    assertString(contentKey, 'contentKey');
    await this.initialize();

    const index = await this._getOfflineIndex();
    const nextIndex = index.filter((entry) => entry !== contentKey);

    await Promise.all([
      this._remove(this._offlineKey(contentKey)),
      this._setOfflineIndex(nextIndex),
    ]);
  }

  async pruneExpiredOfflineContent() {
    await this.initialize();

    const index = await this._getOfflineIndex();

    if (index.length === 0) {
      return [];
    }

    const pairs = await AsyncStorage.multiGet(index.map((contentKey) => this._offlineKey(contentKey)));
    const expiredContentKeys = [];

    for (const [storageKey, rawValue] of pairs) {
      if (rawValue === null) {
        expiredContentKeys.push(storageKey.replace(this._storageKey('offline:'), ''));
        continue;
      }

      const envelope = this._parseEnvelope(rawValue, storageKey);

      if (isExpired(envelope)) {
        expiredContentKeys.push(storageKey.replace(this._storageKey('offline:'), ''));
      }
    }

    if (expiredContentKeys.length === 0) {
      return [];
    }

    await Promise.all([
      AsyncStorage.multiRemove(expiredContentKeys.map((contentKey) => this._offlineKey(contentKey))),
      this._setOfflineIndex(index.filter((contentKey) => !expiredContentKeys.includes(contentKey))),
    ]);

    expiredContentKeys.forEach((contentKey) => this.cache.delete(this._offlineKey(contentKey)));
    return expiredContentKeys;
  }

  async clearOfflineContent() {
    await this.initialize();

    const index = await this._getOfflineIndex();
    const offlineKeys = index.map((contentKey) => this._offlineKey(contentKey));

    await AsyncStorage.multiRemove(offlineKeys.concat(this.keys.offlineIndex));
    offlineKeys.forEach((key) => this.cache.delete(key));
    this.cache.delete(this.keys.offlineIndex);
  }

  async hydrateCache() {
    await this.initialize();

    const [preferences, profile, settings, session, offlineContent] = await Promise.all([
      this.getUserPreferences(),
      this.getUserProfile(),
      this.getAppSettings(),
      this.getSessionData(),
      this.getAllOfflineContent(),
    ]);

    return {
      preferences,
      profile,
      settings,
      session,
      offlineContent,
    };
  }

  async clearAll() {
    await this.initialize();

    await Promise.all([
      this.clearUserPreferences(),
      this.clearUserProfile(),
      this.clearAppSettings(),
      this.clearSessionData(),
      this.clearOfflineContent(),
    ]);

    this.cache.clear();
  }
}

const localDataManager = new LocalDataManager();

module.exports = {
  LocalDataManager,
  localDataManager,
};

module.exports.default = localDataManager;