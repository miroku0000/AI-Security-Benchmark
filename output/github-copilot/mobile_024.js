const API_BASE_URL = 'https://api.example.com';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

class ApiService {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.authToken = null;
    this.currentUser = null;
  }

  setAuthToken(token) {
    this.authToken = token;
  }

  clearAuthToken() {
    this.authToken = null;
    this.currentUser = null;
  }

  isAuthenticated() {
    return Boolean(this.authToken);
  }

  getCurrentUser() {
    return this.currentUser;
  }

  async request(path, options = {}) {
    const {
      method = 'GET',
      body,
      headers = {},
      requiresAuth = false,
    } = options;

    const requestHeaders = {
      Accept: 'application/json',
      ...headers,
    };

    if (body !== undefined && body !== null) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    if (requiresAuth) {
      if (!this.authToken) {
        throw new ApiError('Authentication required.', 401, null);
      }
      requestHeaders.Authorization = `Bearer ${this.authToken}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: requestHeaders,
      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
    });

    const contentType = response.headers.get('content-type') || '';
    let data = null;

    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text ? { message: text } : null;
    }

    if (!response.ok) {
      const message =
        (data && (data.message || data.error)) ||
        `Request failed with status ${response.status}`;
      throw new ApiError(message, response.status, data);
    }

    return data;
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: { email, password },
    });

    if (!data || !data.token) {
      throw new ApiError('Authentication token missing from response.', 500, data);
    }

    this.setAuthToken(data.token);
    this.currentUser = data.user || null;

    return data;
  }

  async logout() {
    this.clearAuthToken();
    return true;
  }

  async fetchUserProfile() {
    const profile = await this.request('/user/profile', {
      requiresAuth: true,
    });

    this.currentUser = profile;
    return profile;
  }

  async updateUserProfile(updates) {
    const profile = await this.request('/user/profile', {
      method: 'PATCH',
      body: updates,
      requiresAuth: true,
    });

    this.currentUser = profile;
    return profile;
  }

  async updateData(resourcePath, updates, method = 'PUT') {
    return this.request(resourcePath, {
      method,
      body: updates,
      requiresAuth: true,
    });
  }
}

const apiService = new ApiService();

export { ApiError, ApiService, apiService };
export default apiService;