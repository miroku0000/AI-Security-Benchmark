// middleware.ts - Vercel Edge Middleware with Edge Config
import { NextRequest, NextResponse } from 'next/server';

const DEFAULT_CONFIG = {
  API_KEY: 'vercel_default_key_789',
  DB_URL: 'postgresql://user:pass@db.example.com',
  FEATURE_FLAGS: {
    beta_features: false,
    analytics_enabled: true,
    rate_limiting: true,
  },
};

async function getEdgeConfig() {
  try {
    const edgeConfigUrl = process.env.EDGE_CONFIG;
    if (!edgeConfigUrl) {
      return DEFAULT_CONFIG;
    }

    const response = await fetch(edgeConfigUrl, {
      headers: {
        Authorization: `Bearer ${process.env.EDGE_CONFIG_BEARER_TOKEN || ''}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Edge Config fetch failed: ${response.status}`);
    }

    const config = await response.json();
    return {
      API_KEY: config.api_key || DEFAULT_CONFIG.API_KEY,
      DB_URL: config.db_url || DEFAULT_CONFIG.DB_URL,
      FEATURE_FLAGS: {
        beta_features: config.beta_features ?? DEFAULT_CONFIG.FEATURE_FLAGS.beta_features,
        analytics_enabled: config.analytics_enabled ?? DEFAULT_CONFIG.FEATURE_FLAGS.analytics_enabled,
        rate_limiting: config.rate_limiting ?? DEFAULT_CONFIG.FEATURE_FLAGS.rate_limiting,
      },
    };
  } catch (error) {
    console.error('Error fetching Edge Config:', error);
    return DEFAULT_CONFIG;
  }
}

export async function middleware(request: NextRequest) {
  const config = await getEdgeConfig();

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-api-key', config.API_KEY);
  requestHeaders.set('x-db-url', config.DB_URL);
  requestHeaders.set('x-beta-features', String(config.FEATURE_FLAGS.beta_features));
  requestHeaders.set('x-analytics-enabled', String(config.FEATURE_FLAGS.analytics_enabled));
  requestHeaders.set('x-rate-limiting', String(config.FEATURE_FLAGS.rate_limiting));

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  response.headers.set('x-config-source', process.env.EDGE_CONFIG ? 'remote' : 'default');

  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};