const API_BASE_URL = 'https://api.example.com';
const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_HEADERS = Object.freeze({
  Accept: 'application/json',
});

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

function isFormData(value) {
  return typeof FormData !== 'undefined' && value instanceof FormData;
}

function isBlob(value) {
  return typeof Blob !== 'undefined' && value instanceof Blob;
}

function isArrayBuffer(value) {
  return typeof ArrayBuffer !== 'undefined' && value instanceof ArrayBuffer;
}

function normalizeBaseUrl(baseUrl) {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    throw new Error('A valid baseUrl is required.');
  }

  return baseUrl.trim().replace(/\/+$/, '');
}

function normalizePath(path) {
  if (!path) {
    return '';
  }

  const value = String(path);
  return value.startsWith('/') ? value : `/${value}`;
}

function buildUrl(baseUrl, path, queryParams) {
  const url = `${normalizeBaseUrl(baseUrl)}${normalizePath(path)}`;

  if (!queryParams || !isPlainObject(queryParams) || Object.keys(queryParams).length === 0) {
    return url;
  }

  const searchParams = new URLSearchParams();

  Object.entries(queryParams).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null) {
          searchParams.append(key, String(item));
        }
      });
      return;
    }

    searchParams.append(key, String(value));
  });

  const queryString = searchParams.toString();
  return queryString ? `${url}?${queryString}` : url;
}

function normalizeHeaders(headers) {
  const normalized = { ...DEFAULT_HEADERS };

  if (!headers) {
    return normalized;
  }

  Object.entries(headers).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      normalized[key] = value;
    }
  });

  return normalized;
}

function hasHeader(headers, headerName) {
  const target = headerName.toLowerCase();
  return Object.keys(headers).some((header) => header.toLowerCase() === target);
}

function serializeBody(body, headers) {
  if (body === undefined || body === null) {
    return undefined;
  }

  if (
    typeof body === 'string' ||
    isFormData(body) ||
    isBlob(body) ||
    isArrayBuffer(body)
  ) {
    return body;
  }

  if (isPlainObject(body) || Array.isArray(body)) {
    if (!hasHeader(headers, 'Content-Type')) {
      headers['Content-Type'] = 'application/json';
    }
    return JSON.stringify(body);
  }

  return body;
}

async function parseResponse(response) {
  if (response.status === 204) {
    return null;
  }

  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  const raw = await response.text();

  if (!raw) {
    return null;
  }

  if (contentType.includes('application/json')) {
    return JSON.parse(raw);
  }

  return raw;
}

function buildError(message, details) {
  const error = new Error(message);
  Object.assign(error, details);
  return error;
}

async function performRequest(config) {
  const {
    baseUrl,
    path,
    method = 'GET',
    headers,
    body,
    query,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    token,
    signal,
  } = config;

  const requestHeaders = normalizeHeaders(headers);

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  const requestBody = serializeBody(body, requestHeaders);
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timeoutId =
    controller && Number.isFinite(timeoutMs) && timeoutMs > 0
      ? setTimeout(() => controller.abort(), timeoutMs)
      : null;

  try {
    const response = await fetch(buildUrl(baseUrl, path, query), {
      method: method.toUpperCase(),
      headers: requestHeaders,
      body: requestBody,
      signal: signal || (controller ? controller.signal : undefined),
    });

    const data = await parseResponse(response);

    if (!response.ok) {
      throw buildError(`Request failed with status ${response.status}`, {
        status: response.status,
        data,
        url: response.url,
      });
    }

    return {
      ok: true,
      status: response.status,
      headers: response.headers,
      data,
      url: response.url,
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      throw buildError(`Request timed out after ${timeoutMs}ms`, {
        code: 'REQUEST_TIMEOUT',
      });
    }

    throw error;
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

function createClient(config) {
  const {
    baseUrl,
    defaultHeaders,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    getAccessToken,
  } = config;

  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const clientHeaders = normalizeHeaders(defaultHeaders);

  async function request(requestConfig) {
    const accessToken =
      typeof getAccessToken === 'function' ? await getAccessToken() : undefined;

    return performRequest({
      ...requestConfig,
      baseUrl: normalizedBaseUrl,
      headers: {
        ...clientHeaders,
        ...(requestConfig && requestConfig.headers ? requestConfig.headers : {}),
      },
      timeoutMs:
        requestConfig && requestConfig.timeoutMs !== undefined
          ? requestConfig.timeoutMs
          : timeoutMs,
      token:
        requestConfig && requestConfig.token !== undefined
          ? requestConfig.token
          : accessToken,
    });
  }

  return {
    request,
    get(path, options) {
      return request({ ...options, method: 'GET', path });
    },
    post(path, body, options) {
      return request({ ...options, method: 'POST', path, body });
    },
    put(path, body, options) {
      return request({ ...options, method: 'PUT', path, body });
    },
    patch(path, body, options) {
      return request({ ...options, method: 'PATCH', path, body });
    },
    delete(path, options) {
      return request({ ...options, method: 'DELETE', path });
    },
  };
}

function buildDeviceBaseUrl(config) {
  const { protocol = 'http', host, port, basePath = '' } = config || {};

  if (typeof host !== 'string' || !host.trim()) {
    throw new Error('A device host is required.');
  }

  const sanitizedHost = host
    .trim()
    .replace(/^https?:\/\//i, '')
    .split('/')[0];

  const normalizedProtocol = protocol === 'https' ? 'https' : 'http';
  const normalizedPort = port ? `:${port}` : '';
  const normalizedBasePath = basePath ? normalizePath(basePath) : '';

  return `${normalizedProtocol}://${sanitizedHost}${normalizedPort}${normalizedBasePath}`;
}

function createApiClient(config) {
  return createClient({
    baseUrl: API_BASE_URL,
    ...config,
  });
}

function createDeviceClient(config) {
  const { baseUrl, ...rest } = config || {};

  return createClient({
    ...rest,
    baseUrl: baseUrl || buildDeviceBaseUrl(rest),
  });
}

const apiClient = createApiClient();

module.exports = {
  API_BASE_URL,
  DEFAULT_TIMEOUT_MS,
  apiClient,
  buildDeviceBaseUrl,
  createApiClient,
  createClient,
  createDeviceClient,
};

module.exports.default = module.exports;