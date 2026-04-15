import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'https://api.example.com';
const AUTH_TOKEN_KEY = '@auth_token';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

type AuthResponse = {
  token: string;
  userId: string;
};

type UserProfile = {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  [key: string]: any;
};

type DataUpdatePayload = Record<string, any>;

type ApiError = {
  status: number;
  message: string;
  details?: any;
};

async function getAuthToken(): Promise<string | null> {
  try {
    const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
    return token;
  } catch (error) {
    console.warn('Error reading auth token', error);
    return null;
  }
}

async function setAuthToken(token: string): Promise<void> {
  try {
    await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch (error) {
    console.warn('Error saving auth token', error);
  }
}

async function clearAuthToken(): Promise<void> {
  try {
    await AsyncStorage.removeItem(AUTH_TOKEN_KEY);
  } catch (error) {
    console.warn('Error clearing auth token', error);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('Content-Type') || '';
  let body: any = null;

  try {
    if (contentType.includes('application/json')) {
      body = await response.json();
    } else {
      body = await response.text();
    }
  } catch {
    body = null;
  }

  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message:
        (body && (body.message || body.error)) ||
        `Request failed with status ${response.status}`,
      details: body,
    };
    throw error;
  }

  return body as T;
}

async function request<T>(
  path: string,
  options: {
    method?: HttpMethod;
    body?: any;
    authenticated?: boolean;
    headers?: Record<string, string>;
  } = {}
): Promise<T> {
  const { method = 'GET', body, authenticated = false, headers = {} } = options;

  const url = `${API_BASE_URL}${path}`;

  const baseHeaders: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...headers,
  };

  if (authenticated) {
    const token = await getAuthToken();
    if (token) {
      baseHeaders.Authorization = `Bearer ${token}`;
    }
  }

  const fetchOptions: RequestInit = {
    method,
    headers: baseHeaders,
  };

  if (body !== undefined && body !== null) {
    fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
  }

  const response = await fetch(url, fetchOptions);
  return handleResponse<T>(response);
}

/**
 * Authentication
 */
async function signIn(email: string, password: string): Promise<AuthResponse> {
  const result = await request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
    authenticated: false,
  });

  if (result && result.token) {
    await setAuthToken(result.token);
  }

  return result;
}

async function signOut(): Promise<void> {
  try {
    const token = await getAuthToken();
    if (token) {
      await request<void>('/auth/logout', {
        method: 'POST',
        authenticated: true,
      });
    }
  } catch (error) {
    console.warn('Error during signOut', error);
  } finally {
    await clearAuthToken();
  }
}

async function isAuthenticated(): Promise<boolean> {
  const token = await getAuthToken();
  return !!token;
}

/**
 * User profile
 */
async function fetchUserProfile(): Promise<UserProfile> {
  return request<UserProfile>('/user/profile', {
    method: 'GET',
    authenticated: true,
  });
}

async function updateUserProfile(
  updates: Partial<UserProfile>
): Promise<UserProfile> {
  return request<UserProfile>('/user/profile', {
    method: 'PATCH',
    body: updates,
    authenticated: true,
  });
}

/**
 * Generic data operations
 */
async function fetchData<T = any>(endpoint: string): Promise<T> {
  return request<T>(endpoint, {
    method: 'GET',
    authenticated: true,
  });
}

async function updateData<T = any>(
  endpoint: string,
  payload: DataUpdatePayload,
  method: 'PUT' | 'PATCH' = 'PUT'
): Promise<T> {
  return request<T>(endpoint, {
    method,
    body: payload,
    authenticated: true,
  });
}

async function postData<T = any>(
  endpoint: string,
  payload: DataUpdatePayload
): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: payload,
    authenticated: true,
  });
}

async function deleteData<T = any>(endpoint: string): Promise<T> {
  return request<T>(endpoint, {
    method: 'DELETE',
    authenticated: true,
  });
}

/**
 * Exported API service
 */
const ApiService = {
  // Auth
  signIn,
  signOut,
  isAuthenticated,
  getAuthToken,

  // User
  fetchUserProfile,
  updateUserProfile,

  // Generic data
  fetchData,
  updateData,
  postData,
  deleteData,
};

export default ApiService;