import AsyncStorage from '@react-native-async-storage/async-storage';

const ENABLE_DEBUG_LOGGING = true; // Toggle or wire to env/config as needed

const SENSITIVE_KEYS = [
  'token',
  'access_token',
  'refresh_token',
  'id_token',
  'auth',
  'authorization',
  'password',
  'pass',
  'secret',
  'ssn',
  'card',
  'cvv',
  'pin',
  'email',
  'phone',
  'address',
  'user',
];

function isObject(value) {
  return value !== null && typeof value === 'object';
}

function redactSensitive(value) {
  if (!isObject(value)) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(redactSensitive);
  }

  const result = {};
  for (const [key, v] of Object.entries(value)) {
    const lowerKey = key.toLowerCase();
    const isSensitive = SENSITIVE_KEYS.some((s) => lowerKey.includes(s));
    if (isSensitive) {
      result[key] = '[REDACTED]';
    } else if (isObject(v)) {
      result[key] = redactSensitive(v);
    } else {
      result[key] = v;
    }
  }
  return result;
}

function safeJsonParse(text) {
  if (typeof text !== 'string') {
    return text;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function stringifyForLog(value) {
  try {
    if (typeof value === 'string') {
      return value;
    }
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

class DebugLogger {
  static initialized = false;
  static originalFetch = null;

  static init(config = {}) {
    if (this.initialized) return;
    this.initialized = true;

    if (config.enableLogging === false) {
      return;
    }

    this.patchFetch();
  }

  static patchFetch() {
    if (!ENABLE_DEBUG_LOGGING) return;
    if (typeof global.fetch !== 'function') return;

    if (!this.originalFetch) {
      this.originalFetch = global.fetch.bind(global);
    }

    const originalFetch = this.originalFetch;

    global.fetch = async (...args) => {
      const startTime = Date.now();
      let url = args[0];
      let options = args[1] || {};

      // Normalize Request object to URL/options if needed
      if (url && typeof url === 'object' && url.url) {
        options = {
          method: url.method,
          headers: url.headers,
          body: url._bodyInit,
          ...options,
        };
        url = url.url;
      }

      let requestBody = options && options.body;
      let parsedRequestBody = requestBody;

      if (typeof requestBody === 'string') {
        parsedRequestBody = safeJsonParse(requestBody);
      }

      const redactedRequestBody = redactSensitive(parsedRequestBody);
      const redactedHeaders = redactSensitive(options && options.headers ? options.headers : {});

      if (ENABLE_DEBUG_LOGGING) {
        console.log('[DebugLogger][NETWORK][REQUEST]', {
          url,
          method: options.method || 'GET',
          headers: redactedHeaders,
          body: redactedRequestBody,
        });
      }

      try {
        const response = await originalFetch(...args);
        const cloned = response.clone ? response.clone() : response;

        let responseBodyText = null;
        try {
          responseBodyText = await cloned.text();
        } catch {
          responseBodyText = null;
        }

        const parsedResponseBody = safeJsonParse(responseBodyText);
        const redactedResponseBody = redactSensitive(parsedResponseBody);

        const durationMs = Date.now() - startTime;

        if (ENABLE_DEBUG_LOGGING) {
          console.debug('[DebugLogger][NETWORK][RESPONSE]', {
            url,
            status: response.status,
            ok: response.ok,
            durationMs,
            body: redactedResponseBody,
          });
        }

        return response;
      } catch (error) {
        const durationMs = Date.now() - startTime;
        if (ENABLE_DEBUG_LOGGING) {
          console.debug('[DebugLogger][NETWORK][ERROR]', {
            url,
            error: error && error.message ? error.message : String(error),
            durationMs,
          });
        }
        throw error;
      }
    };
  }

  static logAsyncStorageOperation(operation, key, value, extra = {}) {
    if (!ENABLE_DEBUG_LOGGING) return;

    let parsedValue = value;
    if (typeof value === 'string') {
      parsedValue = safeJsonParse(value);
    }

    const redactedValue = redactSensitive(parsedValue);

    console.debug('[DebugLogger][ASYNC_STORAGE]', {
      operation,
      key,
      value: redactedValue,
      ...extra,
    });
  }

  static logUserAction(actionName, details = {}) {
    if (!ENABLE_DEBUG_LOGGING) return;

    const redactedDetails = redactSensitive(details);

    console.log('[DebugLogger][USER_ACTION]', {
      action: actionName,
      timestamp: new Date().toISOString(),
      details: redactedDetails,
    });
  }

  static logStateChange(source, prevState, nextState, action = null) {
    if (!ENABLE_DEBUG_LOGGING) return;

    const redactedPrev = redactSensitive(prevState);
    const redactedNext = redactSensitive(nextState);
    const redactedAction = redactSensitive(action);

    console.debug('[DebugLogger][STATE_CHANGE]', {
      source,
      timestamp: new Date().toISOString(),
      action: redactedAction,
      prevState: redactedPrev,
      nextState: redactedNext,
    });
  }
}

const DebugAsyncStorage = {
  async getItem(key) {
    const value = await AsyncStorage.getItem(key);
    DebugLogger.logAsyncStorageOperation('getItem', key, value);
    return value;
  },

  async setItem(key, value) {
    DebugLogger.logAsyncStorageOperation('setItem', key, value, {
      valueLength: typeof value === 'string' ? value.length : undefined,
    });
    return AsyncStorage.setItem(key, value);
  },

  async removeItem(key) {
    DebugLogger.logAsyncStorageOperation('removeItem', key, null);
    return AsyncStorage.removeItem(key);
  },

  async mergeItem(key, value) {
    DebugLogger.logAsyncStorageOperation('mergeItem', key, value);
    return AsyncStorage.mergeItem(key, value);
  },

  async clear() {
    DebugLogger.logAsyncStorageOperation('clear', null, null);
    return AsyncStorage.clear();
  },

  async getAllKeys() {
    const keys = await AsyncStorage.getAllKeys();
    DebugLogger.logAsyncStorageOperation('getAllKeys', null, keys);
    return keys;
  },

  async multiGet(keys) {
    const result = await AsyncStorage.multiGet(keys);
    DebugLogger.logAsyncStorageOperation('multiGet', null, result);
    return result;
  },

  async multiSet(keyValuePairs) {
    DebugLogger.logAsyncStorageOperation('multiSet', null, keyValuePairs);
    return AsyncStorage.multiSet(keyValuePairs);
  },

  async multiRemove(keys) {
    DebugLogger.logAsyncStorageOperation('multiRemove', null, keys);
    return AsyncStorage.multiRemove(keys);
  },

  async multiMerge(keyValuePairs) {
    DebugLogger.logAsyncStorageOperation('multiMerge', null, keyValuePairs);
    return AsyncStorage.multiMerge(keyValuePairs);
  },
};

function createDebugMiddleware(options = {}) {
  const { source = 'redux', logger = DebugLogger } = options;

  return (store) => (next) => (action) => {
    const prevState = store.getState();
    const result = next(action);
    const nextState = store.getState();

    logger.logStateChange(source, prevState, nextState, action);

    return result;
  };
}

function withDebugStateLogging(WrappedComponent, options = {}) {
  const React = require('react');
  const { source = 'component' } = options;

  return class DebugStateLoggerWrapper extends React.PureComponent {
    constructor(props) {
      super(props);
      this.state = {
        debugPrevProps: props,
        debugPrevState: {},
      };
    }

    static getDerivedStateFromProps(nextProps, prevState) {
      const { debugPrevProps } = prevState;
      if (debugPrevProps !== nextProps) {
        DebugLogger.logStateChange(
          source,
          { props: debugPrevProps },
          { props: nextProps },
          { type: 'propsChange' }
        );
        return {
          debugPrevProps: nextProps,
        };
      }
      return null;
    }

    componentDidUpdate(prevProps, prevState) {
      const prev = {
        props: prevProps,
        state: prevState.debugPrevState,
      };
      const next = {
        props: this.props,
        state: this.state.debugPrevState,
      };
      if (prevProps !== this.props || prevState.debugPrevState !== this.state.debugPrevState) {
        DebugLogger.logStateChange(source, prev, next, { type: 'componentDidUpdate' });
      }
    }

    render() {
      return React.createElement(WrappedComponent, this.props);
    }
  };
}

export {
  DebugLogger,
  DebugAsyncStorage,
  createDebugMiddleware,
  withDebugStateLogging,
};