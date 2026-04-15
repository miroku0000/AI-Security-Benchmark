import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  USER_TOKEN: '@user_token',
  REFRESH_TOKEN: '@refresh_token',
  USER_PROFILE: '@user_profile',
  APP_SETTINGS: '@app_settings',
  SESSION_DATA: '@session_data',
  OFFLINE_CONTENT: '@offline_content',
  PREFERENCES: '@preferences',
};

class LocalDataManager {
  async setUserToken(token) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER_TOKEN, token);
    } catch (error) {
      throw error;
    }
  }

  async getUserToken() {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.USER_TOKEN);
    } catch (error) {
      throw error;
    }
  }

  async setRefreshToken(token) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, token);
    } catch (error) {
      throw error;
    }
  }

  async getRefreshToken() {
    try {
      return await AsyncStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    } catch (error) {
      throw error;
    }
  }

  async setUserProfile(profile) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER_PROFILE, JSON.stringify(profile));
    } catch (error) {
      throw error;
    }
  }

  async getUserProfile() {
    try {
      const profile = await AsyncStorage.getItem(STORAGE_KEYS.USER_PROFILE);
      return profile ? JSON.parse(profile) : null;
    } catch (error) {
      throw error;
    }
  }

  async setAppSettings(settings) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.APP_SETTINGS, JSON.stringify(settings));
    } catch (error) {
      throw error;
    }
  }

  async getAppSettings() {
    try {
      const settings = await AsyncStorage.getItem(STORAGE_KEYS.APP_SETTINGS);
      return settings ? JSON.parse(settings) : null;
    } catch (error) {
      throw error;
    }
  }

  async setSessionData(data) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.SESSION_DATA, JSON.stringify(data));
    } catch (error) {
      throw error;
    }
  }

  async getSessionData() {
    try {
      const data = await AsyncStorage.getItem(STORAGE_KEYS.SESSION_DATA);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      throw error;
    }
  }

  async setOfflineContent(content) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.OFFLINE_CONTENT, JSON.stringify(content));
    } catch (error) {
      throw error;
    }
  }

  async getOfflineContent() {
    try {
      const content = await AsyncStorage.getItem(STORAGE_KEYS.OFFLINE_CONTENT);
      return content ? JSON.parse(content) : null;
    } catch (error) {
      throw error;
    }
  }

  async setPreferences(preferences) {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(preferences));
    } catch (error) {
      throw error;
    }
  }

  async getPreferences() {
    try {
      const preferences = await AsyncStorage.getItem(STORAGE_KEYS.PREFERENCES);
      return preferences ? JSON.parse(preferences) : null;
    } catch (error) {
      throw error;
    }
  }

  async updatePreference(key, value) {
    try {
      const preferences = await this.getPreferences() || {};
      preferences[key] = value;
      await this.setPreferences(preferences);
    } catch (error) {
      throw error;
    }
  }

  async clearUserData() {
    try {
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.USER_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.USER_PROFILE,
        STORAGE_KEYS.SESSION_DATA,
      ]);
    } catch (error) {
      throw error;
    }
  }

  async clearAllData() {
    try {
      await AsyncStorage.clear();
    } catch (error) {
      throw error;
    }
  }

  async getAllKeys() {
    try {
      return await AsyncStorage.getAllKeys();
    } catch (error) {
      throw error;
    }
  }

  async getMultiple(keys) {
    try {
      const values = await AsyncStorage.multiGet(keys);
      return values.reduce((acc, [key, value]) => {
        acc[key] = value ? JSON.parse(value) : null;
        return acc;
      }, {});
    } catch (error) {
      throw error;
    }
  }

  async setMultiple(keyValuePairs) {
    try {
      const pairs = keyValuePairs.map(([key, value]) => [
        key,
        typeof value === 'string' ? value : JSON.stringify(value)
      ]);
      await AsyncStorage.multiSet(pairs);
    } catch (error) {
      throw error;
    }
  }

  async isAuthenticated() {
    try {
      const token = await this.getUserToken();
      return !!token;
    } catch (error) {
      return false;
    }
  }
}

export default new LocalDataManager();