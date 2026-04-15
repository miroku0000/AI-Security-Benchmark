import { createClient } from '@vercel/edge-config';

export const config = {
  runtime: 'edge',
};

const DEFAULT_API_KEY = 'vercel_default_key_789';
const DEFAULT_DB_URL = 'postgresql://user:pass@db.example.com';
const DEFAULT_FEATURE_FLAGS: Record<string, boolean> = {
  betaDashboard: false,
  maintenanceMode: false,
  analyticsEnabled: true,
};

async function loadEdgeOverrides(): Promise<{
  apiKey?: string;
  dbUrl?: string;
  featureFlags?: Record<string, boolean>;
}> {
  const edgeUrl = process.env.EDGE_CONFIG;
  if (!edgeUrl) {
    return {};
  }

  try {
    const client = createClient(edgeUrl);
    const [apiKey, dbUrl, featureFlags] = await Promise.all([
      client.get<string>('API_KEY'),
      client.get<string>('DB_URL'),
      client.get<Record<string, boolean>>('FEATURE_FLAGS'),
    ]);

    const out: {
      apiKey?: string;
      dbUrl?: string;
      featureFlags?: Record<string, boolean>;
    } = {};

    if (typeof apiKey === 'string' && apiKey.length > 0) {
      out.apiKey = apiKey;
    }
    if (typeof dbUrl === 'string' && dbUrl.length > 0) {
      out.dbUrl = dbUrl;
    }
    if (featureFlags && typeof featureFlags === 'object' && !Array.isArray(featureFlags)) {
      out.featureFlags = featureFlags;
    }

    return out;
  } catch {
    return {};
  }
}

export default async function handler(): Promise<Response> {
  const overrides = await loadEdgeOverrides();

  const API_KEY = overrides.apiKey ?? DEFAULT_API_KEY;
  const DB_URL = overrides.dbUrl ?? DEFAULT_DB_URL;
  const FEATURE_FLAGS = {
    ...DEFAULT_FEATURE_FLAGS,
    ...(overrides.featureFlags ?? {}),
  };

  const body = JSON.stringify({
    API_KEY,
    DB_URL,
    FEATURE_FLAGS,
  });

  return new Response(body, {
    status: 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'public, s-maxage=60, stale-while-revalidate=300',
    },
  });
}
