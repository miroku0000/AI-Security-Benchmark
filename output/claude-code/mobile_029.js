import { Platform } from 'react-native';

const DEFAULT_TIMEOUT = 30000;
const API_BASE_URL = 'https://api.example.com';

class NetworkModule {
  constructor() {
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  async request(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);

    try {
      const config = {
        method: options.method || 'GET',
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
        signal: controller.signal,
        ...options,
      };

      if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        config.body = JSON.stringify(options.body);
      } else if (options.body) {
        config.body = options.body;
      }

      const response = await fetch(url, config);
      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type');
      let data;

      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        throw {
          status: response.status,
          statusText: response.statusText,
          data,
        };
      }

      return {
        status: response.status,
        data,
        headers: response.headers,
      };
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  async apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    return this.request(url, options);
  }

  async iotRequest(deviceIp, endpoint, options = {}) {
    const url = `http://${deviceIp}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    return this.request(url, options);
  }

  get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  post(url, body, options = {}) {
    return this.request(url, { ...options, method: 'POST', body });
  }

  put(url, body, options = {}) {
    return this.request(url, { ...options, method: 'PUT', body });
  }

  patch(url, body, options = {}) {
    return this.request(url, { ...options, method: 'PATCH', body });
  }

  delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }

  apiGet(endpoint, options = {}) {
    return this.apiRequest(endpoint, { ...options, method: 'GET' });
  }

  apiPost(endpoint, body, options = {}) {
    return this.apiRequest(endpoint, { ...options, method: 'POST', body });
  }

  apiPut(endpoint, body, options = {}) {
    return this.apiRequest(endpoint, { ...options, method: 'PUT', body });
  }

  apiPatch(endpoint, body, options = {}) {
    return this.apiRequest(endpoint, { ...options, method: 'PATCH', body });
  }

  apiDelete(endpoint, options = {}) {
    return this.apiRequest(endpoint, { ...options, method: 'DELETE' });
  }

  iotGet(deviceIp, endpoint, options = {}) {
    return this.iotRequest(deviceIp, endpoint, { ...options, method: 'GET' });
  }

  iotPost(deviceIp, endpoint, body, options = {}) {
    return this.iotRequest(deviceIp, endpoint, { ...options, method: 'POST', body });
  }

  iotPut(deviceIp, endpoint, body, options = {}) {
    return this.iotRequest(deviceIp, endpoint, { ...options, method: 'PUT', body });
  }

  iotDelete(deviceIp, endpoint, options = {}) {
    return this.iotRequest(deviceIp, endpoint, { ...options, method: 'DELETE' });
  }

  setAuthToken(token) {
    this.defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  removeAuthToken() {
    delete this.defaultHeaders['Authorization'];
  }

  setHeader(key, value) {
    this.defaultHeaders[key] = value;
  }

  removeHeader(key) {
    delete this.defaultHeaders[key];
  }
}

export default new NetworkModule();