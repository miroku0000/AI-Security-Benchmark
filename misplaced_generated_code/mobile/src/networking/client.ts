export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

export type RequestBody =
  | string
  | number
  | boolean
  | null
  | undefined
  | ArrayBuffer
  | Uint8Array
  | Blob
  | FormData
  | Record<string, unknown>
  | unknown[];

export type ResponseType = "json" | "text" | "bytes" | "auto";

export type HttpRequestOptions = {
  method?: HttpMethod;
  path?: string;
  url?: string;
  baseUrl?: string;
  query?: QueryParams;
  headers?: Record<string, string | undefined>;
  body?: RequestBody;
  responseType?: ResponseType;
  timeoutMs?: number;
  signal?: AbortSignal;
  authToken?: string;
  fetchImpl?: typeof fetch;
};

export class HttpError extends Error {
  readonly name = "HttpError";
  readonly url: string;
  readonly status: number;
  readonly statusText: string;
  readonly responseText?: string;
  readonly responseJson?: unknown;

  constructor(params: {
    message: string;
    url: string;
    status: number;
    statusText: string;
    responseText?: string;
    responseJson?: unknown;
  }) {
    super(params.message);
    this.url = params.url;
    this.status = params.status;
    this.statusText = params.statusText;
    this.responseText = params.responseText;
    this.responseJson = params.responseJson;
  }
}

export type HttpResponse<T> = {
  ok: boolean;
  url: string;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
};

const DEFAULT_TIMEOUT_MS = 20_000;

function toHeadersRecord(headers: Headers): Record<string, string> {
  const out: Record<string, string> = {};
  headers.forEach((value, key) => {
    out[key.toLowerCase()] = value;
  });
  return out;
}

function isAbsoluteUrl(input: string): boolean {
  return /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(input);
}

function joinUrl(baseUrl: string, path: string): string {
  if (!baseUrl) return path;
  if (!path) return baseUrl;
  if (isAbsoluteUrl(path)) return path;
  const base = baseUrl.replace(/\/+$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function appendQuery(url: string, query?: QueryParams): string {
  if (!query) return url;
  const entries: Array<[string, QueryValue]> = [];
  for (const [k, v] of Object.entries(query)) {
    if (Array.isArray(v)) {
      for (const item of v) entries.push([k, item]);
    } else {
      entries.push([k, v]);
    }
  }

  const pairs: string[] = [];
  for (const [k, v] of entries) {
    if (v === undefined || v === null) continue;
    pairs.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  if (pairs.length === 0) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}${pairs.join("&")}`;
}

function normalizeHeaders(input?: Record<string, string | undefined>): Record<string, string> {
  const out: Record<string, string> = {};
  if (!input) return out;
  for (const [k, v] of Object.entries(input)) {
    if (v === undefined) continue;
    out[k] = v;
  }
  return out;
}

function mergeHeaders(base: Record<string, string>, extra: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(base)) out[k.toLowerCase()] = v;
  for (const [k, v] of Object.entries(extra)) out[k.toLowerCase()] = v;
  return out;
}

function isFormData(x: unknown): x is FormData {
  return typeof FormData !== "undefined" && x instanceof FormData;
}

function isBlob(x: unknown): x is Blob {
  return typeof Blob !== "undefined" && x instanceof Blob;
}

function isUint8Array(x: unknown): x is Uint8Array {
  return typeof Uint8Array !== "undefined" && x instanceof Uint8Array;
}

function isArrayBuffer(x: unknown): x is ArrayBuffer {
  return typeof ArrayBuffer !== "undefined" && x instanceof ArrayBuffer;
}

function shouldSetJsonContentType(body: RequestBody, existingHeaders: Record<string, string>): boolean {
  if (body === undefined || body === null) return false;
  if (typeof body === "string") return false;
  if (typeof body === "number" || typeof body === "boolean") return true;
  if (isFormData(body) || isBlob(body) || isUint8Array(body) || isArrayBuffer(body)) return false;
  const hasContentType = Object.keys(existingHeaders).some((k) => k.toLowerCase() === "content-type");
  return !hasContentType;
}

function encodeBody(body: RequestBody, headers: Record<string, string>): BodyInit | undefined {
  if (body === undefined || body === null) return undefined;
  if (typeof body === "string") return body;
  if (typeof body === "number" || typeof body === "boolean") return JSON.stringify(body);
  if (isFormData(body)) return body;
  if (isBlob(body)) return body;
  if (isUint8Array(body)) return body;
  if (isArrayBuffer(body)) return body;
  if (typeof body === "object") return JSON.stringify(body);
  return JSON.stringify(body);
}

function parseLikelyJson(text: string): unknown {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const first = trimmed[0];
  if (first !== "{" && first !== "[" && first !== '"') return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

async function readBytes(res: Response): Promise<Uint8Array> {
  const ab = await res.arrayBuffer();
  return new Uint8Array(ab);
}

function withTimeout(signal: AbortSignal | undefined, timeoutMs: number): { signal?: AbortSignal; cancel: () => void } {
  if (timeoutMs <= 0) return { signal, cancel: () => {} };
  if (typeof AbortController === "undefined") return { signal, cancel: () => {} };

  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }

  const id = setTimeout(() => controller.abort(), timeoutMs);
  const cancel = () => {
    clearTimeout(id);
    if (signal) signal.removeEventListener("abort", onAbort);
  };
  return { signal: controller.signal, cancel };
}

export async function httpRequest<T = unknown>(opts: HttpRequestOptions): Promise<HttpResponse<T>> {
  const fetchImpl = opts.fetchImpl ?? fetch;
  const method: HttpMethod = (opts.method ?? "GET").toUpperCase() as HttpMethod;

  const baseUrl = opts.baseUrl ?? "";
  const providedUrl = opts.url ?? "";
  const path = opts.path ?? "";
  const url0 = providedUrl ? (isAbsoluteUrl(providedUrl) ? providedUrl : joinUrl(baseUrl, providedUrl)) : joinUrl(baseUrl, path);
  const url = appendQuery(url0, opts.query);

  const defaultHeaders: Record<string, string> = {
    accept: "application/json"
  };

  const authHeaders: Record<string, string> = {};
  if (opts.authToken) authHeaders.authorization = `Bearer ${opts.authToken}`;

  const merged = mergeHeaders(mergeHeaders(defaultHeaders, authHeaders), normalizeHeaders(opts.headers));
  if (shouldSetJsonContentType(opts.body, merged)) merged["content-type"] = "application/json";

  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal, cancel } = withTimeout(opts.signal, timeoutMs);

  try {
    const res = await fetchImpl(url, {
      method,
      headers: merged,
      body: encodeBody(opts.body, merged),
      signal
    });

    const headers = toHeadersRecord(res.headers);
    const responseType: ResponseType = opts.responseType ?? "auto";
    const contentType = headers["content-type"] ?? "";

    const wantsJson =
      responseType === "json" ||
      (responseType === "auto" && (contentType.includes("application/json") || contentType.includes("+json")));

    let data: unknown;
    let responseText: string | undefined;
    let responseJson: unknown | undefined;

    if (responseType === "bytes") {
      data = await readBytes(res);
    } else if (wantsJson) {
      responseText = await res.text();
      const parsed = parseLikelyJson(responseText);
      if (parsed === null && responseText.trim() !== "") {
        responseJson = undefined;
        data = responseText;
      } else {
        responseJson = parsed;
        data = parsed as T;
      }
    } else if (responseType === "text" || responseType === "auto") {
      responseText = await res.text();
      data = responseText as unknown as T;
    } else {
      responseText = await res.text();
      data = responseText as unknown as T;
    }

    if (!res.ok) {
      const message = `HTTP ${res.status} ${res.statusText}`.trim();
      throw new HttpError({
        message,
        url,
        status: res.status,
        statusText: res.statusText,
        responseText,
        responseJson
      });
    }

    return {
      ok: true,
      url,
      status: res.status,
      statusText: res.statusText,
      headers,
      data: data as T
    };
  } finally {
    cancel();
  }
}

export type ApiClientOptions = {
  baseUrl?: string;
  defaultHeaders?: Record<string, string | undefined>;
  getAuthToken?: () => string | undefined | Promise<string | undefined>;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
};

export function createApiClient(opts?: ApiClientOptions) {
  const baseUrl = opts?.baseUrl ?? "https://api.example.com";
  const timeoutMs = opts?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const fetchImpl = opts?.fetchImpl ?? fetch;
  const defaultHeaders = normalizeHeaders(opts?.defaultHeaders);

  async function request<T = unknown>(req: Omit<HttpRequestOptions, "baseUrl" | "fetchImpl" | "timeoutMs" | "authToken">) {
    const token = opts?.getAuthToken ? await opts.getAuthToken() : undefined;
    return httpRequest<T>({
      ...req,
      baseUrl,
      timeoutMs,
      fetchImpl,
      authToken: token,
      headers: mergeHeaders(defaultHeaders, normalizeHeaders(req.headers))
    });
  }

  return { request };
}

export type DeviceClientOptions = {
  scheme?: "http" | "https";
  ip: string;
  port?: number;
  basePath?: string;
  defaultHeaders?: Record<string, string | undefined>;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
};

export function createDeviceClient(opts: DeviceClientOptions) {
  const scheme = opts.scheme ?? "http";
  const port = opts.port;
  const basePath = opts.basePath ?? "";
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const fetchImpl = opts.fetchImpl ?? fetch;
  const defaultHeaders = normalizeHeaders(opts.defaultHeaders);

  const host = port ? `${opts.ip}:${port}` : opts.ip;
  const baseUrl = `${scheme}://${host}${basePath.startsWith("/") || basePath === "" ? basePath : `/${basePath}`}`;

  async function request<T = unknown>(req: Omit<HttpRequestOptions, "baseUrl" | "fetchImpl" | "timeoutMs">) {
    return httpRequest<T>({
      ...req,
      baseUrl,
      timeoutMs,
      fetchImpl,
      headers: mergeHeaders(defaultHeaders, normalizeHeaders(req.headers))
    });
  }

  return { request, baseUrl };
}

