const DEFAULT_API_BASE_URL = 'https://api.example.com';
const DEFAULT_TIMEOUT_MS = 15000;

const DEFAULT_HEADERS = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

function buildHeaders(extraHeaders = {}, authToken) {
  const headers = {
    ...DEFAULT_HEADERS,
    ...extraHeaders,
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  return headers;
}

function withTimeout(promise, timeoutMs = DEFAULT_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error('Request timed out'));
    }, timeoutMs);

    promise
      .then((res) => {
        clearTimeout(timeoutId);
        resolve(res);
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        reject(err);
      });
  });
}

async function handleResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  let body;

  if (contentType.includes('application/json')) {
    body = await response.json().catch(() => null);
  } else {
    body = await response.text().catch(() => null);
  }

  if (!response.ok) {
    const error = new Error('Network request failed');
    error.status = response.status;
    error.statusText = response.statusText;
    error.body = body;
    throw error;
  }

  return body;
}

/**
 * Generic HTTP request helper.
 * Supports both HTTP and HTTPS endpoints.
 */
async function httpRequest({
  url,
  method = 'GET',
  headers = {},
  body,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  authToken,
}) {
  const finalHeaders = buildHeaders(headers, authToken);
  const options = {
    method,
    headers: finalHeaders,
  };

  if (body !== undefined && body !== null) {
    options.body = typeof body === 'string' ? body : JSON.stringify(body);
  }

  const fetchPromise = fetch(url, options).then(handleResponse);
  return withTimeout(fetchPromise, timeoutMs);
}

/**
 * API client for https://api.example.com
 */
export const ApiClient = {
  setBaseUrl(newBaseUrl) {
    this.baseUrl = newBaseUrl;
  },

  baseUrl: DEFAULT_API_BASE_URL,

  buildUrl(path) {
    if (!path) return this.baseUrl;
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    const base = this.baseUrl.endsWith('/')
      ? this.baseUrl.slice(0, -1)
      : this.baseUrl;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${cleanPath}`;
  },

  async get(path, { headers, params, authToken, timeoutMs } = {}) {
    const url = this.addQueryParams(this.buildUrl(path), params);
    return httpRequest({
      url,
      method: 'GET',
      headers,
      authToken,
      timeoutMs,
    });
  },

  async post(path, { headers, body, authToken, timeoutMs } = {}) {
    const url = this.buildUrl(path);
    return httpRequest({
      url,
      method: 'POST',
      headers,
      body,
      authToken,
      timeoutMs,
    });
  },

  async put(path, { headers, body, authToken, timeoutMs } = {}) {
    const url = this.buildUrl(path);
    return httpRequest({
      url,
      method: 'PUT',
      headers,
      body,
      authToken,
      timeoutMs,
    });
  },

  async patch(path, { headers, body, authToken, timeoutMs } = {}) {
    const url = this.buildUrl(path);
    return httpRequest({
      url,
      method: 'PATCH',
      headers,
      body,
      authToken,
      timeoutMs,
    });
  },

  async delete(path, { headers, body, authToken, timeoutMs } = {}) {
    const url = this.buildUrl(path);
    return httpRequest({
      url,
      method: 'DELETE',
      headers,
      body,
      authToken,
      timeoutMs,
    });
  },

  addQueryParams(url, params) {
    if (!params || typeof params !== 'object') return url;
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      if (Array.isArray(value)) {
        value.forEach((v) => searchParams.append(key, String(v)));
      } else {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (!queryString) return url;
    return url.includes('?') ? `${url}&${queryString}` : `${url}?${queryString}`;
  },
};

/**
 * IoT device client for http://192.168.x.x
 * Supports both HTTP and HTTPS based on given deviceUrl.
 */
export const IoTClient = {
  /**
   * Perform a request to a local IoT device.
   * deviceUrl: e.g. "http://192.168.1.10" or "https://192.168.1.10"
   * path: optional path on the device, e.g. "/status"
   */
  async request({
    deviceUrl,
    path = '',
    method = 'GET',
    headers,
    body,
    timeoutMs,
    authToken,
    params,
  }) {
    if (!deviceUrl) {
      throw new Error('deviceUrl is required');
    }

    const base = deviceUrl.endsWith('/')
      ? deviceUrl.slice(0, -1)
      : deviceUrl;
    const cleanPath = path
      ? path.startsWith('/')
        ? path
        : `/${path}`
      : '';
    const urlWithPath = `${base}${cleanPath}`;
    const url = ApiClient.addQueryParams(urlWithPath, params);

    return httpRequest({
      url,
      method,
      headers,
      body,
      timeoutMs,
      authToken,
    });
  },

  async get(deviceUrl, path = '', options = {}) {
    const { headers, authToken, timeoutMs, params } = options;
    return this.request({
      deviceUrl,
      path,
      method: 'GET',
      headers,
      authToken,
      timeoutMs,
      params,
    });
  },

  async post(deviceUrl, path = '', options = {}) {
    const { headers, authToken, timeoutMs, body, params } = options;
    return this.request({
      deviceUrl,
      path,
      method: 'POST',
      headers,
      body,
      authToken,
      timeoutMs,
      params,
    });
  },

  async put(deviceUrl, path = '', options = {}) {
    const { headers, authToken, timeoutMs, body, params } = options;
    return this.request({
      deviceUrl,
      path,
      method: 'PUT',
      headers,
      body,
      authToken,
      timeoutMs,
      params,
    });
  },

  async patch(deviceUrl, path = '', options = {}) {
    const { headers, authToken, timeoutMs, body, params } = options;
    return this.request({
      deviceUrl,
      path,
      method: 'PATCH',
      headers,
      body,
      authToken,
      timeoutMs,
      params,
    });
  },

  async delete(deviceUrl, path = '', options = {}) {
    const { headers, authToken, timeoutMs, body, params } = options;
    return this.request({
      deviceUrl,
      path,
      method: 'DELETE',
      headers,
      body,
      authToken,
      timeoutMs,
      params,
    });
  },
};

/**
 * Example convenience methods that you can extend
 * for specific API endpoints.
 */
export const ApiEndpoints = {
  async getUserProfile({ userId, authToken, timeoutMs } = {}) {
    const path = userId ? `/users/${encodeURIComponent(userId)}` : '/users/me';
    return ApiClient.get(path, { authToken, timeoutMs });
  },

  async updateUserProfile({ userId, data, authToken, timeoutMs } = {}) {
    const path = userId ? `/users/${encodeURIComponent(userId)}` : '/users/me';
    return ApiClient.put(path, {
      body: data,
      authToken,
      timeoutMs,
    });
  },

  async listDevices({ authToken, timeoutMs, params } = {}) {
    return ApiClient.get('/devices', { authToken, timeoutMs, params });
  },
};

/**
 * Example convenience methods for IoT devices.
 */
export const IoTEndpoints = {
  async getDeviceStatus({ deviceUrl, timeoutMs } = {}) {
    return IoTClient.get(deviceUrl, '/status', { timeoutMs });
  },

  async sendDeviceCommand({ deviceUrl, command, timeoutMs } = {}) {
    return IoTClient.post(deviceUrl, '/command', {
      body: command,
      timeoutMs,
    });
  },
};