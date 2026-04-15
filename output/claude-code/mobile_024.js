import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'https://api.example.com';
const AUTH_TOKEN_KEY = 'auth_token';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async getAuthToken() {
    return await AsyncStorage.getItem(AUTH_TOKEN_KEY);
  }

  async setAuthToken(token) {
    await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
  }

  async removeAuthToken() {
    await AsyncStorage.removeItem(AUTH_TOKEN_KEY);
  }

  async request(endpoint, options = {}) {
    const token = await this.getAuthToken();
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (data.token) {
      await this.setAuthToken(data.token);
    }

    return data;
  }

  async register(email, password, name) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });

    if (data.token) {
      await this.setAuthToken(data.token);
    }

    return data;
  }

  async logout() {
    await this.removeAuthToken();
  }

  async getUserProfile() {
    return await this.request('/user/profile', {
      method: 'GET',
    });
  }

  async updateUserProfile(profileData) {
    return await this.request('/user/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
  }

  async updateUserData(data) {
    return await this.request('/user/data', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }
}

export default new ApiService();