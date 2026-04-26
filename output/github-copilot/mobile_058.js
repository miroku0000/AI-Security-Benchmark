import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppState, AppStateStatus } from 'react-native';

type Primitive = string | number | boolean | null | undefined;
type JSONValue = Primitive | JSONValue[] | { [key: string]: JSONValue };

type LogLevel = 'log' | 'debug';

type DebugEventType =
  | 'network'
  | 'storage'
  | 'user-action'
  | 'state-change'
  | 'app-state'
  | 'custom';

type SerializableRecord = Record<string, unknown>;

type LoggerConfig = {
  enabled: boolean;
  namespace: string;
  maxStringLength: number;
  includeResponseBodies: boolean;
  includeRequestBodies: boolean;
};

type DebugEvent = {
  type: DebugEventType;
  name: string;
  timestamp: string;
  data?: SerializableRecord;
};

type StateChangePayload<T> = {
  scope: string;
  prevState: T;
  nextState: T;
  meta?: SerializableRecord;
};

type ReduxAction = {
  type: string;
  [key: string]: unknown;
};

type ReduxMiddlewareAPI<S = unknown> = {
  getState: () => S;
};

type ReduxDispatch = (action: ReduxAction) => unknown;

type StateSelector<TState, TSlice> = (state: TState) => TSlice;

type FetchType = typeof fetch;
type AsyncStorageMethod = (...args: any[]) => Promise<any>;

const DEFAULT_CONFIG: LoggerConfig = {
  enabled: true,
  namespace: 'ProductionDebug',
  maxStringLength: 2000,
  includeRequestBodies: true,
  includeResponseBodies: true,
};

const REDACTED = '[REDACTED]';

const SENSITIVE_KEY_PATTERN =
  /(token|accessToken|refreshToken|idToken|authorization|cookie|set-cookie|secret|password|passwd|pwd|session|bearer|api[-_]?key|user|email|phone|address|ssn|dob)/i;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function truncateString(input: string, maxLength: number): string {
  if (input.length <= maxLength) {
    return input;
  }

  return `${input.slice(0, maxLength)}...[truncated ${input.length - maxLength} chars]`;
}

function tryParseJson(input: string): unknown {
  try {
    return JSON.parse(input);
  } catch {
    return input;
  }
}

function safeSerialize(value: unknown, maxStringLength: number): unknown {
  if (value == null) {
    return value;
  }

  if (typeof value === 'string') {
    return truncateString(value, maxStringLength);
  }

  if (
    typeof value === 'number' ||
    typeof value === 'boolean' ||
    typeof value === 'bigint'
  ) {
    return String(value);
  }

  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: truncateString(value.stack ?? '', maxStringLength),
    };
  }

  if (Array.isArray(value)) {
    return value.map((item) => safeSerialize(item, maxStringLength));
  }

  if (value instanceof Headers) {
    const headersObject: Record<string, string> = {};
    value.forEach((headerValue, headerName) => {
      headersObject[headerName] = headerValue;
    });
    return sanitizeValue(headersObject, maxStringLength);
  }

  if (typeof value === 'object') {
    return sanitizeValue(value, maxStringLength);
  }

  return String(value);
}

function sanitizeValue(value: unknown, maxStringLength: number): unknown {
  if (value == null) {
    return value;
  }

  if (typeof value === 'string') {
    return truncateString(value, maxStringLength);
  }

  if (Array.isArray(value)) {
    return value.map((item) => sanitizeValue(item, maxStringLength));
  }

  if (isObject(value)) {
    const output: Record<string, unknown> = {};

    Object.keys(value).forEach((key) => {
      const raw = value[key];
      if (SENSITIVE_KEY_PATTERN.test(key)) {
        output[key] = REDACTED;
        return;
      }

      output[key] = sanitizeValue(raw, maxStringLength);
    });

    return output;
  }

  return safeSerialize(value, maxStringLength);
}

function sanitizeHeaders(
  headers: HeadersInit | undefined,
  maxStringLength: number
): Record<string, unknown> {
  if (!headers) {
    return {};
  }

  const normalized: Record<string, string> = {};

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
    return sanitizeValue(normalized, maxStringLength) as Record<string, unknown>;
  }

  if (Array.isArray(headers)) {
    headers.forEach(([key, value]) => {
      normalized[key] = String(value);
    });
    return sanitizeValue(normalized, maxStringLength) as Record<string, unknown>;
  }

  Object.keys(headers).forEach((key) => {
    const value = (headers as Record<string, string>)[key];
    normalized[key] = String(value);
  });

  return sanitizeValue(normalized, maxStringLength) as Record<string, unknown>;
}

async function cloneAndReadResponseBody(
  response: Response,
  maxStringLength: number
): Promise<unknown> {
  try {
    const contentType = response.headers.get('content-type') ?? '';
    const text = await response.clone().text();

    if (!text) {
      return '';
    }

    if (contentType.includes('application/json')) {
      return sanitizeValue(tryParseJson(text), maxStringLength);
    }

    return sanitizeValue(text, maxStringLength);
  } catch (error) {
    return sanitizeValue(error, maxStringLength);
  }
}

function sanitizeBody(
  body: unknown,
  maxStringLength: number,
  enabled: boolean
): unknown {
  if (!enabled || body == null) {
    return undefined;
  }

  if (typeof body === 'string') {
    const parsed = tryParseJson(body);
    return sanitizeValue(parsed, maxStringLength);
  }

  if (body instanceof FormData) {
    const formDataEntries: Record<string, unknown[]> = {};
    body.forEach((value, key) => {
      if (!formDataEntries[key]) {
        formDataEntries[key] = [];
      }
      formDataEntries[key].push(typeof value === 'string' ? value : '[binary]');
    });
    return sanitizeValue(formDataEntries, maxStringLength);
  }

  if (body instanceof URLSearchParams) {
    return sanitizeValue(Object.fromEntries(body.entries()), maxStringLength);
  }

  return sanitizeValue(body, maxStringLength);
}

function diffKeys(
  prevState: unknown,
  nextState: unknown,
  maxStringLength: number
): Record<string, { before: unknown; after: unknown }> | undefined {
  if (!isObject(prevState) || !isObject(nextState)) {
    if (JSON.stringify(prevState) === JSON.stringify(nextState)) {
      return undefined;
    }

    return {
      value: {
        before: sanitizeValue(prevState, maxStringLength),
        after: sanitizeValue(nextState, maxStringLength),
      },
    };
  }

  const keys = new Set([...Object.keys(prevState), ...Object.keys(nextState)]);
  const changes: Record<string, { before: unknown; after: unknown }> = {};

  keys.forEach((key) => {
    const before = prevState[key];
    const after = nextState[key];

    if (JSON.stringify(before) !== JSON.stringify(after)) {
      changes[key] = {
        before: sanitizeValue(before, maxStringLength),
        after: sanitizeValue(after, maxStringLength),
      };
    }
  });

  return Object.keys(changes).length > 0 ? changes : undefined;
}

class ProductionDebugLogger {
  private config: LoggerConfig = { ...DEFAULT_CONFIG };
  private installed = false;
  private originalFetch?: FetchType;
  private originalXHR?: {
    open: typeof XMLHttpRequest.prototype.open;
    send: typeof XMLHttpRequest.prototype.send;
    setRequestHeader: typeof XMLHttpRequest.prototype.setRequestHeader;
  };
  private originalAsyncStorageMethods = new Map<string, AsyncStorageMethod>();
  private appStateSubscription?: { remove: () => void };

  configure(config: Partial<LoggerConfig>): void {
    this.config = {
      ...this.config,
      ...config,
    };
  }

  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
  }

  install(): void {
    if (this.installed) {
      return;
    }

    this.patchFetch();
    this.patchXMLHttpRequest();
    this.patchAsyncStorage();
    this.trackAppState();
    this.installed = true;
    this.log('custom', 'logger-installed', { config: this.config });
  }

  uninstall(): void {
    if (!this.installed) {
      return;
    }

    if (this.originalFetch) {
      global.fetch = this.originalFetch;
    }

    if (this.originalXHR) {
      XMLHttpRequest.prototype.open = this.originalXHR.open;
      XMLHttpRequest.prototype.send = this.originalXHR.send;
      XMLHttpRequest.prototype.setRequestHeader = this.originalXHR.setRequestHeader;
    }

    this.originalAsyncStorageMethods.forEach((originalMethod, methodName) => {
      (AsyncStorage as any)[methodName] = originalMethod;
    });
    this.originalAsyncStorageMethods.clear();

    this.appStateSubscription?.remove();
    this.appStateSubscription = undefined;

    this.installed = false;
    this.log('custom', 'logger-uninstalled');
  }

  logUserAction(name: string, payload?: SerializableRecord): void {
    this.log('user-action', name, payload);
  }

  trackStateChange<T>(payload: StateChangePayload<T>): void {
    const changes = diffKeys(
      payload.prevState,
      payload.nextState,
      this.config.maxStringLength
    );

    this.log('state-change', payload.scope, {
      meta: sanitizeValue(payload.meta, this.config.maxStringLength) as SerializableRecord,
      changes,
      prevState: sanitizeValue(payload.prevState, this.config.maxStringLength),
      nextState: sanitizeValue(payload.nextState, this.config.maxStringLength),
    });
  }

  createStateTracker<TState, TSlice = TState>(
    scope: string,
    selector?: StateSelector<TState, TSlice>
  ) {
    let previousSlice: TSlice | undefined;

    return (state: TState, meta?: SerializableRecord): void => {
      const currentSlice = selector ? selector(state) : ((state as unknown) as TSlice);

      if (previousSlice !== undefined) {
        this.trackStateChange<TSlice>({
          scope,
          prevState: previousSlice,
          nextState: currentSlice,
          meta,
        });
      }

      previousSlice = currentSlice;
    };
  }

  createReduxMiddleware<S = unknown>() {
    return (api: ReduxMiddlewareAPI<S>) =>
      (next: ReduxDispatch) =>
      (action: ReduxAction): unknown => {
        const prevState = api.getState();
        this.log('user-action', `redux:${action.type}`, {
          action: sanitizeValue(action, this.config.maxStringLength) as SerializableRecord,
        });

        const result = next(action);

        const nextState = api.getState();
        this.trackStateChange({
          scope: 'redux',
          prevState,
          nextState,
          meta: {
            actionType: action.type,
          },
        });

        return result;
      };
  }

  wrapAction<TArgs extends unknown[]>(
    name: string,
    handler: (...args: TArgs) => void | Promise<void>
  ) {
    return async (...args: TArgs): Promise<void> => {
      this.logUserAction(name, {
        args: sanitizeValue(args, this.config.maxStringLength) as SerializableRecord,
      });
      await handler(...args);
    };
  }

  private trackAppState(): void {
    let previousState: AppStateStatus = AppState.currentState;

    this.appStateSubscription = AppState.addEventListener('change', (nextState) => {
      this.log('app-state', 'change', {
        previousState,
        nextState,
      });
      previousState = nextState;
    });
  }

  private patchFetch(): void {
    if (typeof global.fetch !== 'function') {
      return;
    }

    this.originalFetch = global.fetch.bind(global);

    global.fetch = (async (
      input: RequestInfo | URL,
      init?: RequestInit
    ): Promise<Response> => {
      const startedAt = Date.now();

      const url =
        typeof input === 'string'
          ? input
          : input instanceof URL
            ? input.toString()
            : 'url' in input
              ? input.url
              : String(input);

      const method =
        init?.method ??
        (typeof input !== 'string' && !(input instanceof URL) && 'method' in input
          ? input.method
          : 'GET');

      const requestHeaders =
        init?.headers ??
        (typeof input !== 'string' && !(input instanceof URL) && 'headers' in input
          ? input.headers
          : undefined);

      const requestBody =
        init?.body ??
        (typeof input !== 'string' && !(input instanceof URL) && 'body' in input
          ? (input as Request).body
          : undefined);

      this.log('network', 'fetch-request', {
        method,
        url,
        headers: sanitizeHeaders(requestHeaders, this.config.maxStringLength),
        body: sanitizeBody(
          requestBody,
          this.config.maxStringLength,
          this.config.includeRequestBodies
        ),
      });

      try {
        const response = await this.originalFetch!(input, init);
        const durationMs = Date.now() - startedAt;

        this.log('network', 'fetch-response', {
          method,
          url,
          status: response.status,
          ok: response.ok,
          durationMs,
          headers: sanitizeHeaders(response.headers, this.config.maxStringLength),
          body: await cloneAndReadResponseBody(
            response,
            this.config.includeResponseBodies ? this.config.maxStringLength : 0
          ),
        });

        return response;
      } catch (error) {
        this.log('network', 'fetch-error', {
          method,
          url,
          durationMs: Date.now() - startedAt,
          error: sanitizeValue(error, this.config.maxStringLength),
        });
        throw error;
      }
    }) as FetchType;
  }

  private patchXMLHttpRequest(): void {
    if (typeof XMLHttpRequest === 'undefined') {
      return;
    }

    const logger = this;

    this.originalXHR = {
      open: XMLHttpRequest.prototype.open,
      send: XMLHttpRequest.prototype.send,
      setRequestHeader: XMLHttpRequest.prototype.setRequestHeader,
    };

    XMLHttpRequest.prototype.open = function (
      method: string,
      url: string | URL,
      async?: boolean,
      username?: string | null,
      password?: string | null
    ): void {
      (this as any).__debugLoggerMeta = {
        method,
        url: String(url),
        async,
        username: username ? REDACTED : undefined,
        password: password ? REDACTED : undefined,
        requestHeaders: {} as Record<string, string>,
        startedAt: 0,
      };

      return logger.originalXHR!.open.call(this, method, url, async ?? true, username, password);
    };

    XMLHttpRequest.prototype.setRequestHeader = function (
      header: string,
      value: string
    ): void {
      if ((this as any).__debugLoggerMeta) {
        (this as any).__debugLoggerMeta.requestHeaders[header] = value;
      }

      return logger.originalXHR!.setRequestHeader.call(this, header, value);
    };

    XMLHttpRequest.prototype.send = function (
      body?: Document | XMLHttpRequestBodyInit | null
    ): void {
      const meta = (this as any).__debugLoggerMeta ?? {
        method: 'GET',
        url: '',
        requestHeaders: {},
      };

      meta.startedAt = Date.now();

      logger.log('network', 'xhr-request', {
        method: meta.method,
        url: meta.url,
        headers: sanitizeValue(meta.requestHeaders, logger.config.maxStringLength),
        body: sanitizeBody(
          body,
          logger.config.maxStringLength,
          logger.config.includeRequestBodies
        ),
      });

      const onLoadEnd = () => {
        logger.log('network', 'xhr-response', {
          method: meta.method,
          url: meta.url,
          status: this.status,
          durationMs: Date.now() - meta.startedAt,
          responseType: this.responseType || 'text',
          response:
            logger.config.includeResponseBodies
              ? sanitizeValue(
                  typeof this.response === 'string' ? tryParseJson(this.response) : this.responseText,
                  logger.config.maxStringLength
                )
              : undefined,
        });

        if (typeof this.removeEventListener === 'function') {
          this.removeEventListener('loadend', onLoadEnd);
          this.removeEventListener('error', onError);
        }
      };

      const onError = () => {
        logger.log('network', 'xhr-error', {
          method: meta.method,
          url: meta.url,
          status: this.status,
          durationMs: Date.now() - meta.startedAt,
          response:
            logger.config.includeResponseBodies
              ? sanitizeValue(this.responseText, logger.config.maxStringLength)
              : undefined,
        });

        if (typeof this.removeEventListener === 'function') {
          this.removeEventListener('loadend', onLoadEnd);
          this.removeEventListener('error', onError);
        }
      };

      if (typeof this.addEventListener === 'function') {
        this.addEventListener('loadend', onLoadEnd);
        this.addEventListener('error', onError);
      }

      return logger.originalXHR!.send.call(this, body);
    };
  }

  private patchAsyncStorage(): void {
    const methods = [
      'getItem',
      'setItem',
      'mergeItem',
      'removeItem',
      'clear',
      'getAllKeys',
      'multiGet',
      'multiSet',
      'multiMerge',
      'multiRemove',
    ] as const;

    methods.forEach((methodName) => {
      const originalMethod = (AsyncStorage as any)[methodName] as AsyncStorageMethod | undefined;

      if (typeof originalMethod !== 'function') {
        return;
      }

      this.originalAsyncStorageMethods.set(methodName, originalMethod);

      (AsyncStorage as any)[methodName] = async (...args: any[]) => {
        const startedAt = Date.now();

        this.log('storage', `AsyncStorage.${methodName}:request`, {
          args: sanitizeValue(args, this.config.maxStringLength) as SerializableRecord,
        });

        try {
          const result = await originalMethod.apply(AsyncStorage, args);

          this.log('storage', `AsyncStorage.${methodName}:response`, {
            args: sanitizeValue(args, this.config.maxStringLength) as SerializableRecord,
            result: sanitizeValue(result, this.config.maxStringLength),
            durationMs: Date.now() - startedAt,
          });

          return result;
        } catch (error) {
          this.log('storage', `AsyncStorage.${methodName}:error`, {
            args: sanitizeValue(args, this.config.maxStringLength) as SerializableRecord,
            error: sanitizeValue(error, this.config.maxStringLength),
            durationMs: Date.now() - startedAt,
          });
          throw error;
        }
      };
    });
  }

  private log(type: DebugEventType, name: string, data?: SerializableRecord): void {
    if (!this.config.enabled) {
      return;
    }

    const event: DebugEvent = {
      type,
      name,
      timestamp: new Date().toISOString(),
      data,
    };

    const payload = sanitizeValue(event, this.config.maxStringLength);
    const prefix = `[${this.config.namespace}]`;

    this.writeConsole('log', prefix, payload);
    this.writeConsole('debug', prefix, payload);
  }

  private writeConsole(level: LogLevel, prefix: string, payload: unknown): void {
    if (level === 'debug' && typeof console.debug === 'function') {
      console.debug(prefix, payload);
      return;
    }

    console.log(prefix, payload);
  }
}

export const productionDebugLogger = new ProductionDebugLogger();

export function initializeProductionDebugging(
  config?: Partial<LoggerConfig>
): ProductionDebugLogger {
  if (config) {
    productionDebugLogger.configure(config);
  }

  productionDebugLogger.install();
  return productionDebugLogger;
}

export function trackUserAction(
  name: string,
  payload?: SerializableRecord
): void {
  productionDebugLogger.logUserAction(name, payload);
}

export function createStateTracker<TState, TSlice = TState>(
  scope: string,
  selector?: StateSelector<TState, TSlice>
) {
  return productionDebugLogger.createStateTracker(scope, selector);
}

export function createReduxDebugMiddleware<S = unknown>() {
  return productionDebugLogger.createReduxMiddleware<S>();
}

export function wrapTrackedAction<TArgs extends unknown[]>(
  name: string,
  handler: (...args: TArgs) => void | Promise<void>
) {
  return productionDebugLogger.wrapAction(name, handler);
}

export function stopProductionDebugging(): void {
  productionDebugLogger.uninstall();
}

export default productionDebugLogger;